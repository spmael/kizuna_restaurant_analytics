from django.contrib import admin
from django.contrib.admin import AdminSite
from django.db.models import Avg, Count, Sum
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import DataUpload, ProcessingError
from .tasks import process_data_upload


class DataManagementAdminSite(AdminSite):
    """Custom admin site for data management"""

    site_header = _("Kizuna Restaurant Analytics - Data Management")
    site_title = _("Data Management Admin")
    index_title = _("Data Management Dashboard")

    def index(self, request, extra_context=None):
        """Custom index view with statistics"""

        # Get statistics
        total_uploads = DataUpload.objects.count()
        pending_uploads = DataUpload.objects.filter(status="pending").count()
        processing_uploads = DataUpload.objects.filter(status="processing").count()
        completed_uploads = DataUpload.objects.filter(status="completed").count()
        failed_uploads = DataUpload.objects.filter(status="failed").count()

        # Recent uploads
        recent_uploads = DataUpload.objects.select_related("uploaded_by").order_by(
            "-created_at"
        )[:10]

        # Processing statistics
        total_records_processed = (
            DataUpload.objects.filter(status="completed").aggregate(
                total=Sum("processed_records")
            )["total"]
            or 0
        )

        total_errors = (
            DataUpload.objects.filter(status="completed").aggregate(
                total=Sum("error_records")
            )["total"]
            or 0
        )

        # Average processing time
        avg_processing_time = DataUpload.objects.filter(
            status="completed",
            start_processing_at__isnull=False,
            completed_processing_at__isnull=False,
        ).aggregate(avg_time=Avg("completed_processing_at" - "start_processing_at"))[
            "avg_time"
        ]

        # File type distribution
        file_type_stats = (
            DataUpload.objects.values("file_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Error statistics
        error_stats = (
            ProcessingError.objects.values("error_type")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        extra_context = extra_context or {}
        extra_context.update(
            {
                "total_uploads": total_uploads,
                "pending_uploads": pending_uploads,
                "processing_uploads": processing_uploads,
                "completed_uploads": completed_uploads,
                "failed_uploads": failed_uploads,
                "total_records_processed": total_records_processed,
                "total_errors": total_errors,
                "avg_processing_time": avg_processing_time,
                "file_type_stats": file_type_stats,
                "error_stats": error_stats,
                "recent_uploads": recent_uploads,
            }
        )

        return super().index(request, extra_context)


# Create custom admin site instance
data_management_admin = DataManagementAdminSite(name="data_management_admin")


@admin.register(ProcessingError)
class ProcessingErrorAdmin(admin.ModelAdmin):
    """Admin interface for processing errors"""

    list_display = [
        "upload_file_name",
        "row_number",
        "error_type",
        "error_message_short",
        "created_at",
    ]
    list_filter = [
        "error_type",
        "created_at",
        ("upload", admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = ["upload__original_file_name", "error_message", "column_name"]
    readonly_fields = [
        "upload",
        "row_number",
        "column_name",
        "error_type",
        "error_message",
        "raw_data",
        "created_at",
    ]
    ordering = ["-created_at"]

    def upload_file_name(self, obj):
        """Display upload file name with link"""
        if obj.upload:
            url = reverse(
                "admin:data_management_dataupload_change", args=[obj.upload.id]
            )
            return format_html(
                '<a href="{}">{}</a>', url, obj.upload.original_file_name
            )
        return "-"

    upload_file_name.short_description = _("Upload File")
    upload_file_name.admin_order_field = "upload__original_file_name"

    def error_message_short(self, obj):
        """Display shortened error message"""
        if len(obj.error_message) > 100:
            return obj.error_message[:100] + "..."
        return obj.error_message

    error_message_short.short_description = _("Error Message")

    def has_add_permission(self, request):
        """Disable adding errors manually"""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable editing errors"""
        return False


class ProcessingErrorInline(admin.TabularInline):
    """Inline display of processing errors"""

    model = ProcessingError
    extra = 0
    readonly_fields = [
        "row_number",
        "column_name",
        "error_type",
        "error_message",
        "created_at",
    ]
    fields = [
        "row_number",
        "column_name",
        "error_type",
        "error_message",
        "created_at",
    ]

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DataUpload)
class DataUploadAdmin(admin.ModelAdmin):
    """Admin interface for data uploads"""

    list_display = [
        "original_file_name",
        "file_type",
        "status_badge",
        "uploaded_by",
        "current_stage_display",
        "overall_progress_display",
        "total_records",
        "processed_records",
        "error_records",
        "created_at",
        "processing_duration",
    ]

    list_filter = [
        "status",
        "file_type",
        "uploaded_by",
        "created_at",
        "start_processing_at",
        "completed_processing_at",
    ]

    search_fields = [
        "original_file_name",
        "uploaded_by__username",
        "uploaded_by__email",
        "error_message",
    ]

    readonly_fields = [
        "id",
        "file_size",
        "total_records",
        "processed_records",
        "error_records",
        "start_processing_at",
        "completed_processing_at",
        "processing_duration",
        "progress_percentage",
        "success_rate",
        "processing_log_formatted",
        "sheet_statistics_display",
        "data_quality_summary_display",
    ]

    fieldsets = (
        (
            _("File Information"),
            {"fields": ("id", "file", "original_file_name", "file_size", "file_type")},
        ),
        (
            _("Processing Status"),
            {
                "fields": (
                    "status",
                    "total_records",
                    "processed_records",
                    "error_records",
                    "progress_percentage",
                    "success_rate",
                )
            },
        ),
        (
            _("Sheet-Level Statistics"),
            {
                "fields": ("sheet_statistics_display",),
                "classes": ("collapse",),
            },
        ),
        (
            _("Data Quality Analysis"),
            {
                "fields": ("data_quality_summary_display",),
                "classes": ("collapse",),
            },
        ),
        (
            _("Timing"),
            {
                "fields": (
                    "start_processing_at",
                    "completed_processing_at",
                    "processing_duration",
                )
            },
        ),
        (_("User Information"), {"fields": ("uploaded_by",)}),
        (
            _("Processing Details"),
            {
                "fields": ("error_message", "processing_log_formatted"),
                "classes": ("collapse",),
            },
        ),
    )

    inlines = [ProcessingErrorInline]

    actions = [
        "retry_processing",
        "mark_as_completed",
        "mark_as_failed",
        "delete_selected_uploads",
    ]

    ordering = ["-created_at"]

    def status_badge(self, obj):
        """Display status as a colored badge"""
        status_colors = {
            "pending": "orange",
            "processing": "blue",
            "completed": "green",
            "failed": "red",
            "cancelled": "gray",
        }

        color = status_colors.get(obj.status, "gray")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = _("Status")
    status_badge.admin_order_field = "status"

    def progress_bar(self, obj):
        """Display progress as a progress bar"""
        percentage = obj.progress_percentage()
        if percentage == 0:
            return "-"

        color = "green" if obj.status == "completed" else "blue"
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border-radius: 10px; overflow: hidden;">'
            '<div style="width: {}%; height: 20px; background-color: {}; text-align: center; line-height: 20px; color: white; font-size: 11px;">'
            "{}%</div></div>",
            percentage,
            color,
            percentage,
        )

    progress_bar.short_description = _("Progress")

    def processing_duration(self, obj):
        """Calculate and display processing duration"""
        if obj.start_processing_at and obj.completed_processing_at:
            duration = obj.completed_processing_at - obj.start_processing_at
            return str(duration).split(".")[0]  # Remove microseconds
        elif obj.start_processing_at and obj.status == "processing":
            duration = timezone.now() - obj.start_processing_at
            return f"{str(duration).split('.')[0]} (running)"
        return "-"

    processing_duration.short_description = _("Duration")

    def processing_log_formatted(self, obj):
        """Display processing log with formatting"""
        if obj.processing_log:
            return format_html(
                '<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px;">{}</pre>',
                obj.processing_log,
            )
        return "-"

    processing_log_formatted.short_description = _("Processing Log")

    def sheet_progress_summary(self, obj):
        """Display sheet-level progress summary"""
        if not obj.sheet_statistics:
            return "-"

        summary_parts = []
        for sheet_type, stats in obj.sheet_statistics.items():
            progress = obj.get_sheet_progress(sheet_type)
            total = stats.get("total_records", 0)
            processed = stats.get("created", 0) + stats.get("updated", 0)

            # Color based on progress
            if progress == 100:
                color = "green"
            elif progress > 0:
                color = "orange"
            else:
                color = "red"

            summary_parts.append(
                f'<span style="color: {color}; font-weight: bold;">'
                f"{sheet_type.title()}: {processed}/{total}"
                f"</span>"
            )

        return format_html("<br>".join(summary_parts))

    sheet_progress_summary.short_description = _("Sheet Progress")

    def sheet_statistics_display(self, obj):
        """Display detailed sheet statistics"""
        if not obj.sheet_statistics:
            return "No statistics available"

        html_parts = []
        for sheet_type, stats in obj.sheet_statistics.items():
            progress = obj.get_sheet_progress(sheet_type)

            html_parts.append(
                '<div style="margin-bottom: 15px; padding: 10px; background-color: #f9f9f9; border-radius: 5px;">'
            )
            html_parts.append(
                f'<h4 style="margin: 0 0 10px 0; color: #333;">{sheet_type.title()} Sheet</h4>'
            )

            # Progress bar
            color = "green" if progress == 100 else "orange" if progress > 0 else "red"
            html_parts.append(
                f'<div style="width: 200px; background-color: #e0e0e0; border-radius: 10px; overflow: hidden; margin-bottom: 10px;">'
                f'<div style="width: {progress}%; height: 20px; background-color: {color}; text-align: center; line-height: 20px; color: white; font-size: 11px;">'
                f"{progress}%</div></div>"
            )

            # Statistics table
            html_parts.append('<table style="width: 100%; font-size: 12px;">')
            for key, value in stats.items():
                html_parts.append(
                    f'<tr><td style="padding: 2px; font-weight: bold;">{key.replace("_", " ").title()}:</td><td style="padding: 2px;">{value}</td></tr>'
                )
            html_parts.append("</table>")
            html_parts.append("</div>")

        return format_html("".join(html_parts))

    sheet_statistics_display.short_description = _("Sheet Statistics")

    def current_stage_display(self, obj):
        """Display current processing stage"""
        stage_name = obj.get_stage_display_name()
        if obj.status == "processing":
            return format_html(
                '<span style="color: #007bff; font-weight: bold;">{}</span>',
                stage_name
            )
        elif obj.status == "completed":
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">{}</span>',
                stage_name
            )
        elif obj.status == "failed":
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">{}</span>',
                stage_name
            )
        else:
            return format_html(
                '<span style="color: #6c757d;">{}</span>',
                stage_name
            )

    current_stage_display.short_description = _("Current Stage")

    def overall_progress_display(self, obj):
        """Display overall progress with stage information"""
        if obj.status == "completed":
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">100% Complete</span>'
            )
        elif obj.status == "failed":
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">Failed</span>'
            )
        elif obj.status == "processing":
            progress = obj.get_overall_progress()
            return format_html(
                '<div style="width: 100px; background-color: #f0f0f0; border-radius: 10px; overflow: hidden;">'
                '<div style="width: {}%; height: 20px; background-color: #007bff; text-align: center; '
                'line-height: 20px; color: white; font-size: 11px;">{}%</div></div>',
                progress, progress
            )
        else:
            return format_html(
                '<span style="color: #6c757d;">Pending</span>'
            )

    overall_progress_display.short_description = _("Progress")

    def data_quality_summary_display(self, obj):
        """Display data quality summary"""
        quality_summary = obj.get_data_quality_summary()
        if not quality_summary:
            return "No quality metrics available"

        html_lines = []
        
        # Overall quality score
        overall_score = quality_summary.get("overall_quality_score", 0)
        score_color = "#28a745" if overall_score >= 80 else "#ffc107" if overall_score >= 60 else "#dc3545"
        html_lines.append(
            f'<div style="margin-bottom: 15px;">'
            f'<strong>Overall Quality Score:</strong> '
            f'<span style="color: {score_color}; font-weight: bold; font-size: 16px;">{overall_score}%</span>'
            f'</div>'
        )

        # Summary statistics
        html_lines.append('<div style="margin-bottom: 15px;">')
        html_lines.append(f'<strong>Sheets Analyzed:</strong> {quality_summary.get("sheets_analyzed", 0)}<br>')
        html_lines.append(f'<strong>Total Issues:</strong> {quality_summary.get("total_issues", 0)}<br>')
        html_lines.append(f'<strong>Critical Issues:</strong> {quality_summary.get("critical_issues", 0)}<br>')
        html_lines.append(f'<strong>Warnings:</strong> {quality_summary.get("warnings", 0)}')
        html_lines.append('</div>')

        # Per-sheet details
        if quality_summary.get("sheet_details"):
            html_lines.append('<div style="margin-top: 15px;">')
            html_lines.append('<strong>Per-Sheet Quality:</strong>')
            html_lines.append('<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">')
            html_lines.append('<tr style="background-color: #f8f9fa;">')
            html_lines.append('<th style="border: 1px solid #dee2e6; padding: 8px; text-align: left;">Sheet</th>')
            html_lines.append('<th style="border: 1px solid #dee2e6; padding: 8px; text-align: center;">Quality</th>')
            html_lines.append('<th style="border: 1px solid #dee2e6; padding: 8px; text-align: center;">Records</th>')
            html_lines.append('<th style="border: 1px solid #dee2e6; padding: 8px; text-align: center;">Issues</th>')
            html_lines.append('</tr>')

            for sheet_type, details in quality_summary["sheet_details"].items():
                quality_score = details.get("quality_score", 0)
                score_color = "#28a745" if quality_score >= 80 else "#ffc107" if quality_score >= 60 else "#dc3545"
                
                html_lines.append('<tr>')
                html_lines.append(f'<td style="border: 1px solid #dee2e6; padding: 8px;">{sheet_type.title()}</td>')
                html_lines.append(f'<td style="border: 1px solid #dee2e6; padding: 8px; text-align: center;">'
                                f'<span style="color: {score_color}; font-weight: bold;">{quality_score}%</span></td>')
                html_lines.append(f'<td style="border: 1px solid #dee2e6; padding: 8px; text-align: center;">'
                                f'{details.get("record_count", 0):,}</td>')
                html_lines.append(f'<td style="border: 1px solid #dee2e6; padding: 8px; text-align: center;">'
                                f'{details.get("total_issues", 0)}</td>')
                html_lines.append('</tr>')

            html_lines.append('</table>')
            html_lines.append('</div>')

        return format_html("".join(html_lines))

    data_quality_summary_display.short_description = _("Data Quality Summary")

    def retry_processing(self, request, queryset):
        """Retry processing for selected uploads"""
        count = 0
        for upload in queryset.filter(status__in=["failed", "cancelled"]):
            try:
                upload.status = "pending"
                upload.error_message = ""
                upload.processing_log = ""
                upload.save()

                # Start processing
                process_data_upload.delay(str(upload.id))
                count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Failed to retry processing for {upload.original_file_name}: {str(e)}",
                    level="ERROR",
                )

        self.message_user(
            request, f"Successfully queued {count} uploads for reprocessing."
        )

    retry_processing.short_description = _("Retry processing for selected uploads")

    def mark_as_completed(self, request, queryset):
        """Mark selected uploads as completed"""
        count = queryset.update(
            status="completed", completed_processing_at=timezone.now()
        )
        self.message_user(request, f"Marked {count} uploads as completed.")

    mark_as_completed.short_description = _("Mark as completed")

    def mark_as_failed(self, request, queryset):
        """Mark selected uploads as failed"""
        count = queryset.update(status="failed", completed_processing_at=timezone.now())
        self.message_user(request, f"Marked {count} uploads as failed.")

    mark_as_failed.short_description = _("Mark as failed")

    def delete_selected_uploads(self, request, queryset):
        """Delete selected uploads and their files"""
        count = 0
        for upload in queryset:
            try:
                # Delete the physical file
                if upload.file and upload.file.storage.exists(upload.file.name):
                    upload.file.delete(save=False)

                # Delete the database record
                upload.delete()
                count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Failed to delete {upload.original_file_name}: {str(e)}",
                    level="ERROR",
                )

        self.message_user(
            request, f"Successfully deleted {count} uploads and their files."
        )

    delete_selected_uploads.short_description = _("Delete selected uploads and files")

    def get_queryset(self, request):
        """Add annotations for better performance"""
        return (
            super()
            .get_queryset(request)
            .select_related("uploaded_by")
            .prefetch_related("errors")
        )

    def has_add_permission(self, request):
        """Disable adding uploads through admin"""
        return False

    def has_change_permission(self, request, obj=None):
        """Allow editing but not changing file"""
        return True

    def has_delete_permission(self, request, obj=None):
        """Allow deletion"""
        return True


# Custom admin site configuration
admin.site.site_header = _("Kizuna Restaurant Analytics - Data Management")
admin.site.site_title = _("Data Management Admin")
admin.site.index_title = _("Data Management Dashboard")

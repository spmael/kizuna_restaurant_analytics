import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DetailView, ListView

from .forms import DataFilterForm, DataUploadForm
from .models import DataUpload, ProcessingError
from .tasks import process_data_upload

logger = logging.getLogger(__name__)


class DataUploadView(LoginRequiredMixin, CreateView):
    """View for uploading data files"""

    model = DataUpload
    form_class = DataUploadForm
    template_name = "data_management/upload.html"
    success_url = reverse_lazy("data_management:upload")

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)

        # Start background processing
        try:
            logger.info(f"Starting background processing for upload {self.object.id}")
            process_data_upload.delay(str(self.object.id))
            messages.success(
                self.request,
                _(
                    "Data file uploaded successfully! Processing will start in the background."
                ),
            )
            # Redirect to progress page instead of staying on upload form
            logger.info(f"Redirecting to progress page for upload {self.object.id}")
            return redirect("data_management:upload_progress", upload_id=self.object.id)
        except Exception as e:
            logger.error(
                f"Failed to start processing for upload {self.object.id}: {str(e)}"
            )
            messages.error(
                self.request,
                _(
                    "Data file uploaded successfully! But failed to start processing: {}".format(
                        str(e)
                    )
                ),
            )
        return response

    def form_invalid(self, form):
        """Handle invalid form submission"""
        messages.error(self.request, _("Please correct the errors in the form."))
        return super().form_invalid(form)


class DataUploadListView(LoginRequiredMixin, ListView):
    """View for listing data uploads"""

    model = DataUpload
    template_name = "data_management/upload_list.html"
    context_object_name = "uploads"
    paginate_by = 10

    def get_queryset(self):
        """Filter uploads by user"""
        queryset = DataUpload.objects.filter(uploaded_by=self.request.user)

        # Apply filters
        form = DataFilterForm(self.request.GET)
        if form.is_valid():
            # Filter by status
            if form.cleaned_data["status"]:
                queryset = queryset.filter(status=form.cleaned_data["status"])

            # Filter by file type
            if form.cleaned_data["file_type"]:
                queryset = queryset.filter(file_type=form.cleaned_data["file_type"])

            # Filter by date range
            if form.cleaned_data["date_from"]:
                queryset = queryset.filter(
                    created_at__date__gte=form.cleaned_data["date_from"]
                )

            if form.cleaned_data["date_to"]:
                queryset = queryset.filter(
                    created_at__date__lte=form.cleaned_data["date_to"]
                )

        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        """Add filter form to context"""
        context = super().get_context_data(**kwargs)
        context["filter_form"] = DataFilterForm(self.request.GET)
        return context


class DataUploadDetailView(LoginRequiredMixin, DetailView):
    """View for viewing a single data upload"""

    model = DataUpload
    template_name = "data_management/upload_detail.html"
    context_object_name = "upload"

    def get_queryset(self):
        """Only allow users to view their own uploads"""
        return DataUpload.objects.filter(uploaded_by=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get processing errors
        context["errors"] = ProcessingError.objects.filter(upload=self.object).order_by(
            "row_number"
        )[:50]

        context["total_errors"] = ProcessingError.objects.filter(
            upload=self.object
        ).count()

        return context


@login_required
def upload_progress(request, upload_id):
    """View for checking upload progress"""
    upload = get_object_or_404(DataUpload, id=upload_id, uploaded_by=request.user)

    logger.info(
        f"Progress page accessed for upload {upload_id}, status: {upload.status}"
    )

    # Add some debugging information
    context = {
        "upload": upload,
        "debug_info": {
            "upload_id": str(upload.id),
            "status": upload.status,
            "current_stage": upload.current_stage,
            "stage_progress": upload.stage_progress,
            "completed_stages": upload.completed_stages,
            "total_stages": upload.total_stages,
            "overall_progress": upload.get_overall_progress(),
        },
    }

    return render(request, "data_management/upload_progress.html", context)


@login_required
def dashboard_stats(request):
    """Dashboard statistics for data management"""

    # Get user's uploads
    user_uploads = DataUpload.objects.filter(uploaded_by=request.user)

    stats = {
        "total_uploads": user_uploads.count(),
        "pending_uploads": user_uploads.filter(status="pending").count(),
        "processing_uploads": user_uploads.filter(status="processing").count(),
        "completed_uploads": user_uploads.filter(status="completed").count(),
        "failed_uploads": user_uploads.filter(status="failed").count(),
    }

    recent_uploads = user_uploads.order_by("-created_at")[:5]

    return render(
        request,
        "data_management/dashboard_stats.html",
        {"stats": stats, "recent_uploads": recent_uploads},
    )


@login_required
def recent_uploads_partial(request):
    """Return only recent uploads data for HTMX loading"""

    # Get user's recent uploads
    user_uploads = DataUpload.objects.filter(uploaded_by=request.user)
    recent_uploads = user_uploads.order_by("-created_at")[:5]

    return render(
        request,
        "data_management/recent_uploads_partial.html",
        {"recent_uploads": recent_uploads},
    )


@login_required
def admin_dashboard(request):
    """Admin dashboard with comprehensive statistics"""

    # Check if user is staff
    if not request.user.is_staff:
        messages.error(request, _("Access denied. Staff privileges required."))
        return redirect("data_management:upload")

    # Get comprehensive statistics
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

    # User activity
    user_activity = (
        DataUpload.objects.values("uploaded_by__username")
        .annotate(
            upload_count=Count("id"),
            completed_count=Count("id", filter=Q(status="completed")),
            failed_count=Count("id", filter=Q(status="failed")),
        )
        .order_by("-upload_count")[:10]
    )

    # Daily upload trends (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_uploads = (
        DataUpload.objects.filter(created_at__gte=thirty_days_ago)
        .extra(select={"day": "date(created_at)"})
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    context = {
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
        "user_activity": user_activity,
        "daily_uploads": daily_uploads,
    }

    return render(request, "admin/data_management/dashboard.html", context)


@login_required
def data_quality_report(request):
    """Data quality overview"""

    # Local import for restaurant_data app models avoiding circular import
    from apps.recipes.models import Recipe
    from apps.restaurant_data.models import Product, Purchase, Sales

    # Get comprehensive quality metrics from recent uploads
    recent_uploads = (
        DataUpload.objects.filter(
            status="completed", data_quality_metrics__isnull=False
        )
        .exclude(data_quality_metrics={})
        .order_by("-created_at")[:5]
    )

    # Aggregate quality metrics from recent uploads
    aggregated_quality_stats = {}
    total_quality_score = 0
    total_uploads_with_quality = 0

    for upload in recent_uploads:
        if upload.data_quality_metrics:
            quality_summary = upload.get_data_quality_summary()
            if quality_summary:
                total_quality_score += quality_summary.get("overall_quality_score", 0)
                total_uploads_with_quality += 1

                # Merge sheet details
                for sheet_type, details in quality_summary.get(
                    "sheet_details", {}
                ).items():
                    if sheet_type not in aggregated_quality_stats:
                        aggregated_quality_stats[sheet_type] = {
                            "quality_score": 0,
                            "record_count": 0,
                            "valid_records": 0,
                            "invalid_records": 0,
                            "completeness": 0,
                            "accuracy": 0,
                            "consistency": 0,
                            "total_issues": 0,
                            "critical_issues": 0,
                            "warnings": 0,
                            "issues": [],
                            "upload_count": 0,
                        }

                    stats = aggregated_quality_stats[sheet_type]
                    stats["quality_score"] += details.get("quality_score", 0)
                    stats["record_count"] += details.get("record_count", 0)
                    stats["valid_records"] += details.get("valid_records", 0)
                    stats["invalid_records"] += details.get("invalid_records", 0)
                    stats["completeness"] += details.get("completeness", 0)
                    stats["accuracy"] += details.get("accuracy", 0)
                    stats["consistency"] += details.get("consistency", 0)
                    stats["total_issues"] += details.get("total_issues", 0)
                    stats["critical_issues"] += details.get("critical_issues", 0)
                    stats["warnings"] += details.get("warnings", 0)
                    stats["issues"].extend(details.get("issues", []))
                    stats["upload_count"] += 1

    # Calculate averages for aggregated stats
    for sheet_type, stats in aggregated_quality_stats.items():
        if stats["upload_count"] > 0:
            stats["quality_score"] = round(
                stats["quality_score"] / stats["upload_count"], 2
            )
            stats["completeness"] = round(
                stats["completeness"] / stats["upload_count"], 2
            )
            stats["accuracy"] = round(stats["accuracy"] / stats["upload_count"], 2)
            stats["consistency"] = round(
                stats["consistency"] / stats["upload_count"], 2
            )
            # Keep only unique issues
            stats["issues"] = list(set(stats["issues"]))[
                :10
            ]  # Limit to 10 most common issues

    # Calculate overall quality score
    overall_quality_score = (
        round(total_quality_score / total_uploads_with_quality, 2)
        if total_uploads_with_quality > 0
        else 0
    )

    # Prepare quality stats for template
    quality_stats = {
        "overall_quality_score": overall_quality_score,
        "sheets_analyzed": len(aggregated_quality_stats),
        "total_issues": sum(
            stats.get("total_issues", 0) for stats in aggregated_quality_stats.values()
        ),
        "critical_issues": sum(
            stats.get("critical_issues", 0)
            for stats in aggregated_quality_stats.values()
        ),
        "warnings": sum(
            stats.get("warnings", 0) for stats in aggregated_quality_stats.values()
        ),
        "sheet_details": aggregated_quality_stats,
    }

    # Add legacy statistics for backward compatibility
    quality_stats.update(
        {
            "products": {
                "total": Product.objects.count(),
                "with_purchases": Product.objects.filter(purchases__isnull=False)
                .distinct()
                .count(),
                "with_sales": Product.objects.filter(sales__isnull=False)
                .distinct()
                .count(),
            },
            "sales": {
                "total": Sales.objects.count(),
            },
            "purchases": {
                "total": Purchase.objects.count(),
            },
            "recipes": {
                "total": Recipe.objects.count(),
                "with_ingredients": Recipe.objects.annotate(
                    total_ingredients=Count("ingredients")
                )
                .filter(total_ingredients__gt=0)
                .count(),
            },
            "uploads": {
                "total": DataUpload.objects.count(),
                "completed": DataUpload.objects.filter(status="completed").count(),
                "failed": DataUpload.objects.filter(status="failed").count(),
                "processing": DataUpload.objects.filter(status="processing").count(),
            },
            "errors": {
                "total": ProcessingError.objects.count(),
                "recent": ProcessingError.objects.filter(
                    created_at__gte=timezone.now() - timedelta(days=7)
                ).count(),
            },
        }
    )

    return render(
        request,
        "data_management/data_quality_report.html",
        {
            "quality_stats": quality_stats,
            "title": _("Data Quality Report"),
        },
    )


@login_required
def test_progress(request):
    """Test view to check if progress tracking is working"""

    # Create a test upload for debugging
    test_upload, created = DataUpload.objects.get_or_create(
        original_file_name="test_progress.xlsx",
        defaults={
            "uploaded_by": request.user,
            "file_type": "odoo_export",
            "status": "processing",
            "current_stage": "extracting",
            "stage_progress": 25,
            "completed_stages": 0,
            "total_stages": 5,
        },
    )

    if not created:
        # Update existing test upload
        test_upload.status = "processing"
        test_upload.current_stage = "extracting"
        test_upload.stage_progress = 25
        test_upload.completed_stages = 0
        test_upload.save()

    logger.info(f"Test progress view accessed, test upload ID: {test_upload.id}")

    return redirect("data_management:upload_progress", upload_id=test_upload.id)


@login_required
def check_progress_ajax(request, upload_id):
    """AJAX endpoint to check upload progress"""
    from django.http import JsonResponse

    try:
        upload = DataUpload.objects.get(id=upload_id, uploaded_by=request.user)

        progress_data = {
            "status": upload.status,
            "current_stage": upload.current_stage,
            "stage_progress": upload.stage_progress,
            "completed_stages": upload.completed_stages,
            "total_stages": upload.total_stages,
            "overall_progress": upload.get_overall_progress(),
            "processed_records": upload.processed_records,
            "error_records": upload.error_records,
            "total_records": upload.total_records,
        }

        return JsonResponse(progress_data)

    except DataUpload.DoesNotExist:
        return JsonResponse({"error": "Upload not found"}, status=404)

import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel

User = get_user_model()


class DataUpload(TimeStampedModel):
    """Track data uploads for products, purchases, and sales"""

    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("processing", _("Processing")),
        ("completed", _("Completed")),
        ("failed", _("Failed")),
        ("cancelled", _("Cancelled")),
    ]

    FILE_TYPE_CHOICES = [
        ("odoo_export", _("Odoo Export")),
        ("other", _("Other")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # File information
    file = models.FileField(
        _("Data File"),
        upload_to="uploads/%Y/%m",
        help_text=_("Upload the data file to be imported"),
    )
    original_file_name = models.CharField(_("Original File Name"), max_length=255)
    file_size = models.PositiveIntegerField(
        _("File Size (bytes)"), null=True, blank=True
    )
    file_type = models.CharField(
        _("File Type"), max_length=50, choices=FILE_TYPE_CHOICES
    )

    # Processing information
    status = models.CharField(
        _("Status"), max_length=20, choices=STATUS_CHOICES, default="pending"
    )

    # Statistics
    total_records = models.PositiveIntegerField(_("Total Records"), default=0)
    processed_records = models.PositiveIntegerField(_("Processed Records"), default=0)
    error_records = models.PositiveIntegerField(_("Error Records"), default=0)

    # Processing stages and progress
    current_stage = models.CharField(
        _("Current Stage"),
        max_length=50,
        default="pending",
        help_text=_("Current processing stage"),
    )
    stage_progress = models.PositiveIntegerField(
        _("Stage Progress (%)"),
        default=0,
        help_text=_("Progress within current stage (0-100)"),
    )
    total_stages = models.PositiveIntegerField(
        _("Total Stages"), default=5, help_text=_("Total number of processing stages")
    )
    completed_stages = models.PositiveIntegerField(
        _("Completed Stages"), default=0, help_text=_("Number of completed stages")
    )

    # Detailed sheet-level statistics and quality metrics
    sheet_statistics = models.JSONField(
        _("Sheet Statistics"),
        default=dict,
        blank=True,
        help_text=_(
            "Detailed statistics for each sheet type (products, purchases, sales, recipes)"
        ),
    )

    # Data quality metrics
    data_quality_metrics = models.JSONField(
        _("Data Quality Metrics"),
        default=dict,
        blank=True,
        help_text=_("Comprehensive data quality metrics for each sheet"),
    )

    # User tracking
    uploaded_by = models.ForeignKey(
        User,
        verbose_name=_("Uploaded By"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploads",
    )

    # Proccesing details
    start_processing_at = models.DateTimeField(
        _("Start Processing At"), null=True, blank=True
    )
    completed_processing_at = models.DateTimeField(
        _("Completed Processing At"), null=True, blank=True
    )
    error_message = models.TextField(_("Error Message"), null=True, blank=True)
    processing_log = models.TextField(_("Processing Log"), null=True, blank=True)

    class Meta:
        verbose_name = _("Data Upload")
        verbose_name_plural = _("Data Uploads")
        ordering = ["-created_at"]

    def __str__(self):
        return self.original_file_name

    def get_sheet_statistics(self):
        """Get formatted sheet statistics"""
        if not self.sheet_statistics:
            return {}
        return self.sheet_statistics

    def get_sheet_progress(self, sheet_type):
        """Get progress percentage for a specific sheet type"""
        stats = self.sheet_statistics.get(sheet_type, {})
        total = stats.get("total_records", 0)
        processed = stats.get("created", 0) + stats.get("updated", 0)
        if total > 0:
            return int((processed / total) * 100)
        return 0

    def get_all_sheet_progress(self):
        """Get progress for all sheet types"""
        progress = {}
        for sheet_type in self.sheet_statistics:
            progress[sheet_type] = self.get_sheet_progress(sheet_type)
        return progress

    def progress_percentage(self):
        """Calculate progress percentage based on processed records"""
        if self.total_records > 0:
            return int((self.processed_records / self.total_records) * 100)
        return 0

    def success_rate(self):
        """Calculate success ratio based on processed records"""
        if self.total_records > 0:
            return int((self.processed_records / self.total_records) * 100)
        return 0

    def update_stage(self, stage_name: str, progress: int = 0):
        """Update current processing stage and progress"""
        self.current_stage = stage_name
        self.stage_progress = min(100, max(0, progress))
        self.save()

    def complete_stage(self):
        """Mark current stage as completed and move to next"""
        self.completed_stages += 1
        self.stage_progress = 100
        self.save()

    def get_overall_progress(self) -> int:
        """Calculate overall progress percentage across all stages"""
        if self.total_stages == 0:
            return 0
        return int((self.completed_stages / self.total_stages) * 100)

    def get_stage_display_name(self) -> str:
        """Get human-readable stage name"""
        stage_names = {
            "pending": "Waiting to start",
            "extracting": "Extracting data from file",
            "transforming": "Transforming and cleaning data",
            "loading": "Loading data to database",
            "generating_analytics": "Generating consolidated analytics",
            "completed": "Processing completed",
            "failed": "Processing failed",
        }
        return stage_names.get(self.current_stage, self.current_stage.title())

    def get_data_quality_summary(self) -> dict:
        """Get comprehensive data quality summary"""
        if not self.data_quality_metrics:
            return {}

        summary = {
            "overall_quality_score": 0,
            "sheets_analyzed": 0,
            "total_issues": 0,
            "critical_issues": 0,
            "warnings": 0,
            "sheet_details": {},
        }

        total_score = 0
        total_sheets = 0

        for sheet_type, metrics in self.data_quality_metrics.items():
            sheet_score = metrics.get("quality_score", 0)
            total_score += sheet_score
            total_sheets += 1

            summary["total_issues"] += metrics.get("total_issues", 0)
            summary["critical_issues"] += metrics.get("critical_issues", 0)
            summary["warnings"] += metrics.get("warnings", 0)

            summary["sheet_details"][sheet_type] = {
                "quality_score": sheet_score,
                "record_count": metrics.get("record_count", 0),
                "valid_records": metrics.get("valid_records", 0),
                "invalid_records": metrics.get("invalid_records", 0),
                "completeness": metrics.get("completeness", 0),
                "accuracy": metrics.get("accuracy", 0),
                "consistency": metrics.get("consistency", 0),
                "issues": metrics.get("issues", []),
            }

        if total_sheets > 0:
            summary["overall_quality_score"] = round(total_score / total_sheets, 2)
            summary["sheets_analyzed"] = total_sheets

        return summary


class ProcessingError(TimeStampedModel):
    """Track errors during data processing"""

    upload = models.ForeignKey(
        DataUpload, on_delete=models.CASCADE, related_name="errors"
    )
    row_number = models.PositiveIntegerField(_("Row Number"))
    column_name = models.CharField(
        _("Column Name"), max_length=255, blank=True, null=True
    )
    error_type = models.CharField(_("Error Type"), max_length=50)
    error_message = models.TextField(_("Error Message"))
    raw_data = models.JSONField(_("Raw Data"), null=True, blank=True)

    class Meta:
        verbose_name = _("Processing Error")
        verbose_name_plural = _("Processing Errors")
        ordering = ["upload", "row_number"]

    def __str__(self):
        return f"Error in {self.upload.original_file_name} at row {self.row_number}"

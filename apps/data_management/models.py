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
        ("recipes_data", _("Recipes Data")),
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

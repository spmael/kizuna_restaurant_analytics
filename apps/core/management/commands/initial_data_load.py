import os
import sys
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _

from apps.data_management.models import DataUpload
from data_engineering.pipelines.initial_load_pipeline import DataProcessingPipeline

User = get_user_model()


class Command(BaseCommand):
    """
    Load initial data from Excel files into the database using the ETL pipeline.
    """

    help = _(
        "Load initial data from Excel/CSV files into the database using the ETL pipeline."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Path to the Excel/CSV file to load.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run the command without saving changes to the database.",
        )
        parser.add_argument(
            "--user",
            type=str,
            help="Username of the user running the command (defaults to first superuser).",
        )
        parser.add_argument(
            "--skip-quality",
            action="store_true",
            help="Skip data quality analysis stage to speed up processing.",
        )
        parser.add_argument(
            "--quality-sample",
            type=float,
            default=1.0,
            help="Sample fraction for data quality analysis (0<frac<=1).",
        )

    def handle(self, *args, **options):
        file_path = options.get("file")
        dry_run = options.get("dry-run", False)
        username = options.get("user")
        skip_quality = options.get("skip_quality", False)
        quality_sample = options.get("quality_sample", 1.0)

        # Configure console encoding for Windows
        if sys.platform == "win32":
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")

        if not file_path:
            raise CommandError(_("Please provide file path using --file argument."))

        # Convert relative path to absolute if needed
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)

        if not Path(file_path).exists():
            raise CommandError(_("File does not exist: {}".format(file_path)))

        self.stdout.write(
            self.style.SUCCESS(_("Starting to load data from {}".format(file_path)))
        )

        try:
            # Get or create user
            user = self._get_user(username)

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        _("DRY RUN MODE - No changes will be saved to database")
                    )
                )
                # For dry run, we'll just validate the file structure
                self._validate_file_structure(file_path)
                self.stdout.write(
                    self.style.SUCCESS(_("Dry run completed. File structure is valid."))
                )
                return

            # Create DataUpload instance
            upload_instance = self._create_upload_instance(file_path, user)

            # Run the ETL pipeline
            pipeline = DataProcessingPipeline(
                upload_instance,
                enable_quality=not skip_quality,
                quality_sample=quality_sample,
            )
            success = pipeline.process()

            if success:
                self.stdout.write(
                    self.style.SUCCESS(
                        _("Data loaded successfully using ETL pipeline.")
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(_("Upload ID: {}".format(upload_instance.id)))
                )

                # Display summary
                self._display_upload_summary(upload_instance)
            else:
                self.stdout.write(
                    self.style.ERROR(
                        _("Data loading failed. Check the logs for details.")
                    )
                )
                if upload_instance.error_message:
                    self.stdout.write(
                        self.style.ERROR(
                            _("Error: {}".format(upload_instance.error_message))
                        )
                    )

        except Exception as e:
            raise CommandError(_("Error processing file: {}".format(e)))

    def _get_user(self, username):
        """Get user for the upload"""
        if username:
            try:
                return User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(_("User '{}' not found.".format(username)))
        else:
            # Default to first superuser
            superuser = User.objects.filter(is_superuser=True).first()
            if not superuser:
                raise CommandError(
                    _("No superuser found. Please create one or specify --user.")
                )
            return superuser

    def _create_upload_instance(self, file_path, user):
        """Create a DataUpload instance for the file"""
        try:
            # Get file info
            file_path_obj = Path(file_path)
            file_size = file_path_obj.stat().st_size

            # Copy file to media directory if it's not already there
            if not file_path.startswith(str(Path("media").absolute())):
                import shutil

                media_uploads_dir = Path("media/uploads")
                media_uploads_dir.mkdir(parents=True, exist_ok=True)

                # Copy file to media directory
                dest_path = media_uploads_dir / file_path_obj.name
                shutil.copy2(file_path, dest_path)

                self.stdout.write(
                    self.style.SUCCESS(f"Copied file to media directory: {dest_path}")
                )

                # Update file_path to use the copied file
                file_path = str(dest_path)

            # Create upload instance using the file path relative to media directory
            # We need to create a proper file object for Django's FileField
            from django.core.files import File

            with open(file_path, "rb") as f:
                upload = DataUpload.objects.create(
                    file=File(f, name=file_path_obj.name),
                    original_file_name=file_path_obj.name,
                    file_size=file_size,
                    file_type="odoo_export",
                    uploaded_by=user,
                    status="pending",
                )

            self.stdout.write(
                self.style.SUCCESS(f"Created upload instance with ID: {upload.id}")
            )

            return upload

        except Exception as e:
            raise CommandError(f"Error creating upload instance: {str(e)}")

    def _validate_file_structure(self, file_path):
        """Validate the file structure for dry run"""
        try:
            from data_engineering.extractors.odoo_extractor import OdooExtractor

            extractor = OdooExtractor(file_path)
            extracted_data = extractor.extract()

            if not extracted_data:
                raise CommandError(
                    _("File could not be extracted. Check if it's a valid Excel file.")
                )

            self.stdout.write(_("File structure validation successful:"))
            for sheet_name, df in extracted_data.items():
                if df is not None:
                    self.stdout.write(_("  - {}: {} rows".format(sheet_name, len(df))))
                else:
                    self.stdout.write(
                        _("  - {}: ERROR (could not read)".format(sheet_name))
                    )

        except Exception as e:
            raise CommandError(_("File validation failed: {}".format(e)))

    def _display_upload_summary(self, upload_instance):
        """Display summary of the upload results"""
        self.stdout.write(_("\nUpload Summary:"))
        self.stdout.write(_("  Status: {}".format(upload_instance.status)))
        self.stdout.write(
            _("  Total Records: {}".format(upload_instance.total_records))
        )
        self.stdout.write(
            _("  Processed Records: {}".format(upload_instance.processed_records))
        )
        self.stdout.write(
            _("  Error Records: {}".format(upload_instance.error_records))
        )

        if upload_instance.sheet_statistics:
            self.stdout.write(_("\nSheet Statistics:"))
            for sheet_type, stats in upload_instance.sheet_statistics.items():
                if isinstance(stats, dict):
                    self.stdout.write(_("  {}:".format(sheet_type)))
                    for key, value in stats.items():
                        self.stdout.write(_("    {}: {}".format(key, value)))

        if upload_instance.data_quality_metrics:
            self.stdout.write(_("\nData Quality:"))
            overall = upload_instance.data_quality_metrics.get("overall", {})
            if overall:
                self.stdout.write(
                    _("  Overall Score: {}%".format(overall.get("quality_score", 0)))
                )
                self.stdout.write(
                    _("  Total Issues: {}".format(overall.get("total_issues", 0)))
                )
                self.stdout.write(
                    _("  Critical Issues: {}".format(overall.get("critical_issues", 0)))
                )

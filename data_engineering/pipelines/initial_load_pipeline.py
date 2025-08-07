import logging
from typing import Dict, Optional

from django.utils import timezone

from apps.data_management.models import DataUpload, ProcessingError

from ..extractors.odoo_extractor import OdooExtractor, RecipeExtractor
from ..loaders.database_loader import RecipeDataLoader, RestaurantDataLoader
from ..transformers.odoo_data_cleaner import OdooDataTransformer, RecipeDataTransformer

logger = logging.getLogger(__name__)


class DataProcessingPipeline:
    """Complete ETL pipeline for initial data load"""

    def __init__(self, upload_instance: DataUpload):
        self.upload = upload_instance
        self.user = upload_instance.uploaded_by
        self.file_path = upload_instance.file.path
        self.extractor = None
        self.transformer = None
        self.loader = None
        self.stats = {}

    def process(self) -> bool:
        """Run the complete ETL pipeline"""

        try:
            # Update upload status to processing
            self.upload.status = "processing"
            self.upload.start_processing_at = timezone.now()
            self.upload.save()

            # Step 1: Extract data
            extracted_data = self._extract_data()
            if not extracted_data:
                self._handle_error("Data extraction failed")
                return False

            # Step 2: Transform data
            transformed_data = self._transform_data(extracted_data)
            if not transformed_data:
                self._handle_error("Data transformation failed")
                return False

            # Step 3: Load data
            load_results = self._load_data(transformed_data)
            if not load_results:
                self._handle_error("Data loading failed")
                return False

            # Success
            self._handle_success(load_results)

            return True
        except Exception as e:
            error_msg = f"Error processing data: {str(e)}"
            self._handle_error(error_msg)
            return False

    def _extract_data(self) -> Optional[Dict]:
        """Extract data from the uploaded file"""

        try:
            if self.upload.file_type == "odoo_export":
                self.extractor = OdooExtractor(self.file_path)
            elif self.upload.file_type == "recipes_data":
                self.extractor = RecipeExtractor(self.file_path)
            else:
                # Try Odoo extractor as default
                self.extractor = OdooExtractor(self.file_path)

            extracted_data = self.extractor.extract()

            if not extracted_data:
                for error in self.extractor.errors:
                    self._log_processing_error(0, "extraction", error)
                return None

            # Calculate total records
            total_records = sum(df.shape[0] for df in extracted_data.values())
            self.upload.total_records = total_records
            self.upload.save()

            logger.info(
                f"Extracted {total_records} records from {self.upload.file.name}"
            )
            return extracted_data

        except Exception as e:
            logger.error(f"Error extracting data: {str(e)}")
            return None

    def _transform_data(self, extracted_data: Dict) -> Optional[Dict]:
        """Transform extracted data"""

        try:
            if self.upload.file_type == "odoo_export":
                self.transformer = OdooDataTransformer(user=self.user)
                transformed_data = self.transformer.transform(extracted_data)
            elif self.upload.file_type == "recipes_data":
                self.transformer = RecipeDataTransformer(user=self.user)
                transformed_data = self.transformer.transform(extracted_data)

            for error in self.transformer.errors:
                self._log_processing_error(0, "transformation", error)

            for warning in self.transformer.warnings:
                logger.warning(f"Transformation warning: {warning}")

            if not transformed_data:
                logger.error("No transformed data")
                return None

            logger.info(f"Transformed {len(transformed_data)} sheets")
            return transformed_data

        except Exception as e:
            logger.error(f"Error transforming data: {str(e)}")
            return None

    def _load_data(self, transformed_data: Dict) -> Optional[Dict]:
        """Load transformed data into the database"""

        try:
            if self.upload.file_type == "odoo_export":
                self.loader = RestaurantDataLoader(self.user)
                load_results = self.loader.load(transformed_data)
            elif self.upload.file_type == "recipes_data":
                self.loader = RecipeDataLoader(self.user)
                load_results = self.loader.load(transformed_data)

            for error in self.loader.errors:
                self._log_processing_error(0, "loading", error)

            # Update upload statistics
            self.upload.processed_records = (
                self.loader.created_count + self.loader.updated_count
            )
            self.upload.error_records = self.loader.error_count
            self.upload.save()

            logger.info(
                f"Loaded data - Created: {self.loader.created_count}, Updated: {self.loader.updated_count}, Errors: {self.loader.error_count}"
            )
            return load_results

        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            return None

    def _handle_success(self, load_results: Dict):
        """Handle successful data load"""

        self.upload.status = "completed"
        self.upload.end_processing_at = timezone.now()

        # build processing log
        log_lines = [
            f"Processing completed at {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total records processed: {self.upload.processed_records}",
            f"Total errors: {self.upload.error_records}",
            "Results by data type:",
        ]

        for data_type, stats in load_results.items():
            log_lines.append(f"\n{data_type.capitalize()}:")
            for key, value in stats.items():
                log_lines.append(f"  {key}: {value}")

        self.upload.processing_log = "\n".join(log_lines)
        self.upload.save()

        logger.info(f"ETL pipeline completed successfully for upload {self.upload.id}")

    def _handle_error(self, error_msg: str):
        """Handle processing errors"""

        self.upload.status = "failed"
        self.upload.end_processing_at = timezone.now()

        # build error log
        log_lines = [
            f"Processing failed at {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Error: {error_msg}",
        ]

        if (
            hasattr(self.extractor, "errors")
            and self.extractor
            and self.extractor.errors
        ):
            log_lines.append("\nExtraction errors:")
            log_lines.extend(f"  - {error}" for error in self.extractor.errors)

        if (
            hasattr(self.transformer, "errors")
            and self.transformer
            and self.transformer.errors
        ):
            log_lines.append("\nTransformation errors:")
            log_lines.extend(f"  - {error}" for error in self.transformer.errors)

        if hasattr(self.loader, "errors") and self.loader and self.loader.errors:
            log_lines.append("\nLoading errors:")
            log_lines.extend(f"  - {error}" for error in self.loader.errors)

        self.upload.processing_log = "\n".join(log_lines)
        self.upload.save()

        logger.error(f"ETL pipeline failed for upload {self.upload.id}: {error_msg}")

    def _log_processing_error(self, row_number: int, error_type: str, error_msg: str):
        """Log individual processing errors"""

        ProcessingError.objects.create(
            upload=self.upload,
            row_number=row_number,
            error_type=error_type,
            error_message=error_msg,
        )

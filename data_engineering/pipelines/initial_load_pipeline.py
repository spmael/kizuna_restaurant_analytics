import logging
from typing import Dict, Optional

from django.utils import timezone

from apps.data_management.models import DataUpload, ProcessingError

from ..extractors.odoo_extractor import OdooExtractor
from ..loaders.database_loader import RestaurantDataLoader
from ..transformers.odoo_data_cleaner import OdooDataTransformer
from ..utils.data_quality_analyzer import DataQualityAnalyzer

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
        self.quality_analyzer = DataQualityAnalyzer()

    def process(self) -> bool:
        """Run the complete ETL pipeline"""

        try:
            # Initialize processing
            self.upload.status = "processing"
            self.upload.start_processing_at = timezone.now()
            self.upload.total_stages = 5  # Extract, Transform, Load, Analytics, Quality
            self.upload.completed_stages = 0
            self.upload.save()

            # Stage 1: Extract data
            self.upload.update_stage("extracting", 0)
            extracted_data = self._extract_data()
            if not extracted_data:
                self._handle_error("Data extraction failed")
                return False
            self.upload.complete_stage()

            # Stage 2: Transform data
            self.upload.update_stage("transforming", 0)
            transformed_data = self._transform_data(extracted_data)
            if not transformed_data:
                self._handle_error("Data transformation failed")
                return False
            self.upload.complete_stage()

            # Stage 3: Analyze data quality (after transformation)
            self.upload.update_stage("analyzing_quality", 0)
            quality_metrics = self._analyze_data_quality(transformed_data)
            self.upload.complete_stage()

            # Stage 4: Load data
            self.upload.update_stage("loading", 0)
            load_results = self._load_data(transformed_data)
            if not load_results:
                self._handle_error("Data loading failed")
                return False
            self.upload.complete_stage()

            # Stage 5: Generate analytics
            self.upload.update_stage("generating_analytics", 0)
            self._generate_analytics()
            self.upload.complete_stage()

            # Success
            self._handle_success(load_results, quality_metrics)

            return True
        except Exception as e:
            error_msg = f"Error processing data: {str(e)}"
            self._handle_error(error_msg)
            return False

    def _extract_data(self) -> Optional[Dict]:
        """Extract data from the uploaded file"""

        try:
            # Use unified OdooExtractor for all file types
            self.extractor = OdooExtractor(self.file_path)
            extracted_data = self.extractor.extract()

            if not extracted_data:
                for error in self.extractor.errors:
                    self._log_processing_error(0, "extraction", error)
                return None

            # Log extraction statistics
            total_rows = sum(
                len(df) for df in extracted_data.values() if df is not None
            )
            logger.info(
                f"Extracted {len(extracted_data)} sheets with {total_rows} total rows"
            )

            return extracted_data

        except Exception as e:
            error_msg = f"Error extracting data: {str(e)}"
            self._log_processing_error(0, "extraction", error_msg)
            return None

    def _transform_data(self, extracted_data: Dict) -> Optional[Dict]:
        """Transform and clean extracted data"""

        try:
            # Use unified OdooDataTransformer for all data types
            self.transformer = OdooDataTransformer()
            transformed_data = self.transformer.transform(extracted_data)

            if not transformed_data:
                for error in self.transformer.errors:
                    self._log_processing_error(0, "transformation", error)
                return None

            # Log transformation statistics
            total_rows = sum(
                len(df) for df in transformed_data.values() if df is not None
            )
            logger.info(
                f"Transformed {len(transformed_data)} sheets with {total_rows} total rows"
            )

            return transformed_data

        except Exception as e:
            error_msg = f"Error transforming data: {str(e)}"
            self._log_processing_error(0, "transformation", error_msg)
            return None

    def _analyze_data_quality(self, transformed_data: Dict) -> Dict:
        """Analyze data quality for all sheets"""

        try:
            quality_metrics = {}

            for sheet_type, df in transformed_data.items():
                if df is not None and not df.empty:
                    sheet_metrics = self.quality_analyzer.analyze_sheet(df, sheet_type)
                    quality_metrics[sheet_type] = sheet_metrics

            # Calculate overall quality score
            overall_score = self.quality_analyzer.calculate_overall_quality(
                quality_metrics
            )
            quality_metrics["overall"] = {
                "quality_score": overall_score,
                "total_sheets": len(quality_metrics),
                "total_issues": sum(
                    metrics.get("total_issues", 0)
                    for metrics in quality_metrics.values()
                ),
                "critical_issues": sum(
                    metrics.get("critical_issues", 0)
                    for metrics in quality_metrics.values()
                ),
                "warnings": sum(
                    metrics.get("warnings", 0) for metrics in quality_metrics.values()
                ),
            }

            logger.info(
                f"Data quality analysis completed. Overall score: {overall_score}%"
            )
            return quality_metrics

        except Exception as e:
            logger.error(f"Error analyzing data quality: {str(e)}")
            return {}

    def _load_data(self, transformed_data: Dict) -> Optional[Dict]:
        """Load transformed data into database"""

        try:
            # Use unified RestaurantDataLoader for all data types
            self.loader = RestaurantDataLoader(user=self.user, upload=self.upload)
            load_results = self.loader.load(transformed_data)

            if not load_results:
                for error in self.loader.errors:
                    self._log_processing_error(0, "loading", error)
                return None

            # Log loading statistics
            total_created = sum(
                result.get("created", 0)
                for result in load_results.values()
                if isinstance(result, dict)
            )
            total_updated = sum(
                result.get("updated", 0)
                for result in load_results.values()
                if isinstance(result, dict)
            )
            total_errors = sum(
                result.get("errors", 0)
                for result in load_results.values()
                if isinstance(result, dict)
            )

            # Update upload statistics
            self.upload.processed_records = total_created + total_updated
            self.upload.error_records = total_errors
            self.upload.total_records = self.upload.processed_records + total_errors
            self.upload.save()

            logger.info(
                f"Data loading completed. Created: {total_created}, Updated: {total_updated}, Errors: {total_errors}"
            )

            return load_results

        except Exception as e:
            error_msg = f"Error loading data: {str(e)}"
            self._log_processing_error(0, "loading", error_msg)
            return None

    def _handle_success(self, load_results: Dict, quality_metrics: Dict):
        """Handle successful data load"""

        self.upload.status = "completed"
        self.upload.current_stage = "completed"
        self.upload.completed_processing_at = timezone.now()

        # Store detailed sheet statistics and quality metrics
        self.upload.sheet_statistics = load_results
        self.upload.data_quality_metrics = quality_metrics

        # build processing log
        log_lines = [
            f"Processing completed at {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total records processed: {self.upload.processed_records}",
            f"Total errors: {self.upload.error_records}",
            f"Overall progress: {self.upload.get_overall_progress()}%",
            "Results by data type:",
        ]

        for data_type, stats in load_results.items():
            log_lines.append(f"\n{data_type.capitalize()}:")
            for key, value in stats.items():
                log_lines.append(f"  {key}: {value}")

        # Add data quality summary
        if quality_metrics:
            log_lines.append("\nData Quality Summary:")
            quality_summary = self.upload.get_data_quality_summary()
            if quality_summary:
                log_lines.append(
                    f"  Overall Quality Score: {quality_summary.get('overall_quality_score', 0)}%"
                )
                log_lines.append(
                    f"  Sheets Analyzed: {quality_summary.get('sheets_analyzed', 0)}"
                )
                log_lines.append(
                    f"  Total Issues: {quality_summary.get('total_issues', 0)}"
                )
                log_lines.append(
                    f"  Critical Issues: {quality_summary.get('critical_issues', 0)}"
                )
                log_lines.append(f"  Warnings: {quality_summary.get('warnings', 0)}")

        self.upload.processing_log = "\n".join(log_lines)
        self.upload.save()

        logger.info(f"ETL pipeline completed successfully for upload {self.upload.id}")

    def _generate_analytics(self):
        """Generate consolidated analytics data"""
        logger.info("Generating consolidated analytics...")

        # This is handled by the loader's consolidated data generation
        # Just log the stage completion
        logger.info("Analytics generation completed")

    def _handle_error(self, error_msg: str):
        """Handle processing errors"""

        self.upload.status = "failed"
        self.upload.current_stage = "failed"
        self.upload.completed_processing_at = timezone.now()

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

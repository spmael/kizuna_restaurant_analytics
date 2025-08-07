import os
import tempfile
from unittest.mock import patch

import pandas as pd
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.data_management.models import DataUpload, ProcessingError
from data_engineering.pipelines.initial_load_pipeline import DataProcessingPipeline

User = get_user_model()


class TestPipelineIntegration(TestCase):
    """Integration tests for DataProcessingPipeline with real components"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()

        # Create sample Excel file for testing
        self.sample_data = {
            "products": pd.DataFrame(
                {
                    "name": ["Product A", "Product B", "Product C"],
                    "price": [10.50, 15.75, 8.25],
                    "category": ["Food", "Beverage", "Food"],
                }
            ),
            "sales": pd.DataFrame(
                {
                    "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
                    "product": ["Product A", "Product B", "Product C"],
                    "quantity": [5, 3, 2],
                    "total": [52.50, 47.25, 16.50],
                }
            ),
        }

        self.excel_file_path = os.path.join(self.temp_dir, "test_data.xlsx")
        with pd.ExcelWriter(self.excel_file_path, engine="openpyxl") as writer:
            for sheet_name, df in self.sample_data.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)

    def tearDown(self):
        """Clean up test files"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_upload_instance(self, file_path, file_type="odoo_export"):
        """Helper method to create a DataUpload instance"""
        with open(file_path, "rb") as f:
            file_content = f.read()

        uploaded_file = SimpleUploadedFile(
            os.path.basename(file_path),
            file_content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        return DataUpload.objects.create(
            file=uploaded_file,
            original_file_name=os.path.basename(file_path),
            file_type=file_type,
            uploaded_by=self.user,
            status="pending",
        )

    def test_full_pipeline_integration(self):
        """Test full pipeline integration with mocked components"""
        # Create upload instance
        upload = self.create_upload_instance(self.excel_file_path)

        # Mock all components using context managers
        with patch(
            "data_engineering.pipelines.initial_load_pipeline.OdooExtractor"
        ) as mock_extractor_class:
            mock_extractor_instance = mock_extractor_class.return_value
            mock_extractor_instance.extract.return_value = self.sample_data
            mock_extractor_instance.errors = []

            with patch(
                "data_engineering.pipelines.initial_load_pipeline.OdooDataTransformer"
            ) as mock_transformer_class:
                mock_transformer_instance = mock_transformer_class.return_value
                mock_transformer_instance.transform.return_value = {
                    "transformed_products": self.sample_data["products"],
                    "transformed_sales": self.sample_data["sales"],
                }
                mock_transformer_instance.errors = []
                mock_transformer_instance.warnings = []

                with patch(
                    "data_engineering.pipelines.initial_load_pipeline.RestaurantDataLoader"
                ) as mock_loader_class:
                    mock_loader_instance = mock_loader_class.return_value
                    mock_loader_instance.load.return_value = {
                        "restaurant_data": {"created": 3, "updated": 0, "errors": 0}
                    }
                    mock_loader_instance.errors = []
                    mock_loader_instance.created_count = 3
                    mock_loader_instance.updated_count = 0
                    mock_loader_instance.error_count = 0

                    pipeline = DataProcessingPipeline(upload)
                    result = pipeline.process()

                    # Assertions
                    self.assertTrue(result)
                    self.assertEqual(upload.status, "completed")
                    self.assertEqual(upload.total_records, 6)  # 3 products + 3 sales
                    self.assertEqual(upload.processed_records, 3)
                    self.assertEqual(upload.error_records, 0)

                    # Verify component calls
                    mock_extractor_instance.extract.assert_called_once()
                    mock_transformer_instance.transform.assert_called_once_with(
                        self.sample_data
                    )
                    mock_loader_instance.load.assert_called_once()

    def test_pipeline_with_invalid_file(self):
        """Test pipeline behavior with invalid file"""
        # Create an invalid file
        invalid_file_path = os.path.join(self.temp_dir, "invalid.txt")
        with open(invalid_file_path, "w") as f:
            f.write("This is not an Excel file")

        upload = self.create_upload_instance(invalid_file_path)

        # Run pipeline
        pipeline = DataProcessingPipeline(upload)
        result = pipeline.process()

        # Should fail due to invalid file format
        self.assertFalse(result)
        self.assertEqual(upload.status, "failed")
        self.assertIn("Data extraction failed", upload.processing_log)

    def test_pipeline_with_empty_file(self):
        """Test pipeline behavior with empty Excel file"""
        # Create empty Excel file
        empty_file_path = os.path.join(self.temp_dir, "empty.xlsx")
        empty_df = pd.DataFrame()
        with pd.ExcelWriter(empty_file_path, engine="openpyxl") as writer:
            empty_df.to_excel(writer, sheet_name="empty", index=False)

        upload = self.create_upload_instance(empty_file_path)

        # Run pipeline
        pipeline = DataProcessingPipeline(upload)
        result = pipeline.process()

        # Should handle empty file gracefully
        self.assertFalse(result)
        self.assertEqual(upload.status, "failed")

    @patch("data_engineering.extractors.odoo_extractor.OdooExtractor.extract")
    def test_pipeline_with_extraction_errors(self, mock_extract):
        """Test pipeline with extraction errors"""
        # Mock extractor to return None and have errors
        mock_extract.return_value = None

        upload = self.create_upload_instance(self.excel_file_path)

        # Mock the extractor instance to have errors
        with patch(
            "data_engineering.pipelines.initial_load_pipeline.OdooExtractor"
        ) as mock_extractor_class:
            mock_extractor_instance = mock_extractor_class.return_value
            mock_extractor_instance.extract.return_value = None
            mock_extractor_instance.errors = [
                "File format not supported",
                "Missing required columns",
            ]

            pipeline = DataProcessingPipeline(upload)
            result = pipeline.process()

            self.assertFalse(result)
            self.assertEqual(upload.status, "failed")
            self.assertIn("Data extraction failed", upload.processing_log)

            # Check that processing errors were created
            errors = ProcessingError.objects.filter(upload=upload)
            self.assertEqual(errors.count(), 2)

    @patch("data_engineering.extractors.odoo_extractor.OdooExtractor.extract")
    @patch(
        "data_engineering.transformers.odoo_data_cleaner.OdooDataTransformer.transform"
    )
    def test_pipeline_with_transformation_errors(self, mock_transform, mock_extract):
        """Test pipeline with transformation errors"""
        # Mock extractor to succeed
        mock_extract.return_value = self.sample_data

        # Mock transformer to fail
        mock_transform.return_value = None

        upload = self.create_upload_instance(self.excel_file_path)

        # Mock the transformer instance to have errors
        with patch(
            "data_engineering.pipelines.initial_load_pipeline.OdooDataTransformer"
        ) as mock_transformer_class:
            mock_transformer_instance = mock_transformer_class.return_value
            mock_transformer_instance.transform.return_value = None
            mock_transformer_instance.errors = [
                "Invalid data format",
                "Missing required fields",
            ]

            pipeline = DataProcessingPipeline(upload)
            result = pipeline.process()

            self.assertFalse(result)
            self.assertEqual(upload.status, "failed")
            self.assertIn("Data transformation failed", upload.processing_log)

    def test_pipeline_with_loading_errors(self):
        """Test pipeline with loading errors"""
        upload = self.create_upload_instance(self.excel_file_path)

        # Mock all components using context managers
        with patch(
            "data_engineering.pipelines.initial_load_pipeline.OdooExtractor"
        ) as mock_extractor_class:
            mock_extractor_instance = mock_extractor_class.return_value
            mock_extractor_instance.extract.return_value = self.sample_data
            mock_extractor_instance.errors = []

            with patch(
                "data_engineering.pipelines.initial_load_pipeline.OdooDataTransformer"
            ) as mock_transformer_class:
                mock_transformer_instance = mock_transformer_class.return_value
                mock_transformer_instance.transform.return_value = {
                    "transformed_products": self.sample_data["products"],
                    "transformed_sales": self.sample_data["sales"],
                }
                mock_transformer_instance.errors = []
                mock_transformer_instance.warnings = []

                with patch(
                    "data_engineering.pipelines.initial_load_pipeline.RestaurantDataLoader"
                ) as mock_loader_class:
                    mock_loader_instance = mock_loader_class.return_value
                    mock_loader_instance.load.return_value = None
                    mock_loader_instance.errors = [
                        "Database connection failed",
                        "Constraint violation",
                    ]
                    # Set proper integer values for statistics to avoid MagicMock issues
                    mock_loader_instance.created_count = 0
                    mock_loader_instance.updated_count = 0
                    mock_loader_instance.error_count = 2

                    pipeline = DataProcessingPipeline(upload)
                    result = pipeline.process()

                    self.assertFalse(result)
                    self.assertEqual(upload.status, "failed")
                    self.assertIn("Data loading failed", upload.processing_log)

    def test_pipeline_with_recipes_data(self):
        """Test pipeline with recipes data file type"""
        # Create sample recipes data
        recipes_data = pd.DataFrame(
            {
                "recipe_name": ["Pasta Carbonara", "Caesar Salad", "Tiramisu"],
                "ingredients": [
                    "Pasta, Eggs, Bacon",
                    "Lettuce, Croutons, Dressing",
                    "Coffee, Mascarpone, Ladyfingers",
                ],
                "cooking_time": [20, 10, 30],
                "difficulty": ["Medium", "Easy", "Hard"],
            }
        )

        recipes_file_path = os.path.join(self.temp_dir, "recipes.xlsx")
        with pd.ExcelWriter(recipes_file_path, engine="openpyxl") as writer:
            recipes_data.to_excel(writer, sheet_name="recipes", index=False)

        upload = self.create_upload_instance(
            recipes_file_path, file_type="recipes_data"
        )

        # Mock the components for recipes data
        with patch(
            "data_engineering.pipelines.initial_load_pipeline.RecipeExtractor"
        ) as mock_extractor_class:
            mock_extractor_instance = mock_extractor_class.return_value
            mock_extractor_instance.extract.return_value = {"recipes": recipes_data}
            mock_extractor_instance.errors = []

            with patch(
                "data_engineering.pipelines.initial_load_pipeline.RecipeDataTransformer"
            ) as mock_transformer_class:
                mock_transformer_instance = mock_transformer_class.return_value
                mock_transformer_instance.transform.return_value = {
                    "transformed_recipes": recipes_data
                }
                mock_transformer_instance.errors = []
                mock_transformer_instance.warnings = []

                with patch(
                    "data_engineering.pipelines.initial_load_pipeline.RecipeDataLoader"
                ) as mock_loader_class:
                    mock_loader_instance = mock_loader_class.return_value
                    mock_loader_instance.load.return_value = {
                        "recipe_data": {"created": 3}
                    }
                    mock_loader_instance.errors = []
                    mock_loader_instance.created_count = 3
                    mock_loader_instance.updated_count = 0
                    mock_loader_instance.error_count = 0

                    pipeline = DataProcessingPipeline(upload)
                    result = pipeline.process()

                    self.assertTrue(result)
                    self.assertEqual(upload.status, "completed")
                    self.assertEqual(upload.total_records, 3)
                    self.assertEqual(upload.processed_records, 3)

    def test_pipeline_concurrent_processing(self):
        """Test that multiple uploads can be processed concurrently"""
        # Create multiple upload instances
        uploads = []
        for i in range(3):
            upload = self.create_upload_instance(self.excel_file_path)
            uploads.append(upload)

        # Mock the components for all uploads
        with patch(
            "data_engineering.pipelines.initial_load_pipeline.OdooExtractor"
        ) as mock_extractor_class:
            mock_extractor_instance = mock_extractor_class.return_value
            mock_extractor_instance.extract.return_value = self.sample_data
            mock_extractor_instance.errors = []

            with patch(
                "data_engineering.pipelines.initial_load_pipeline.OdooDataTransformer"
            ) as mock_transformer_class:
                mock_transformer_instance = mock_transformer_class.return_value
                mock_transformer_instance.transform.return_value = {
                    "transformed_data": "test"
                }
                mock_transformer_instance.errors = []
                mock_transformer_instance.warnings = []

                with patch(
                    "data_engineering.pipelines.initial_load_pipeline.RestaurantDataLoader"
                ) as mock_loader_class:
                    mock_loader_instance = mock_loader_class.return_value
                    mock_loader_instance.load.return_value = {
                        "restaurant_data": {"created": 3}
                    }
                    mock_loader_instance.errors = []
                    mock_loader_instance.created_count = 3
                    mock_loader_instance.updated_count = 0
                    mock_loader_instance.error_count = 0

                    # Process all uploads
                    pipelines = []
                    for upload in uploads:
                        pipeline = DataProcessingPipeline(upload)
                        result = pipeline.process()
                        pipelines.append((pipeline, result))

                    # Verify all completed successfully
                    for pipeline, result in pipelines:
                        self.assertTrue(result)
                        self.assertEqual(pipeline.upload.status, "completed")

    def test_pipeline_error_logging(self):
        """Test that pipeline errors are properly logged"""
        upload = self.create_upload_instance(self.excel_file_path)

        # Mock extractor to fail with specific errors
        with patch(
            "data_engineering.pipelines.initial_load_pipeline.OdooExtractor"
        ) as mock_extractor_class:
            mock_extractor_instance = mock_extractor_class.return_value
            mock_extractor_instance.extract.return_value = None
            mock_extractor_instance.errors = [
                "Row 5: Invalid product name",
                "Row 12: Missing price information",
                "Row 18: Invalid date format",
            ]

            pipeline = DataProcessingPipeline(upload)
            result = pipeline.process()

            self.assertFalse(result)
            self.assertEqual(upload.status, "failed")

            # Check that processing errors were logged
            errors = ProcessingError.objects.filter(upload=upload)
            self.assertEqual(errors.count(), 3)

            # Check error details
            error_messages = [error.error_message for error in errors]
            self.assertIn("Row 5: Invalid product name", error_messages)
            self.assertIn("Row 12: Missing price information", error_messages)
            self.assertIn("Row 18: Invalid date format", error_messages)

    def test_pipeline_processing_statistics(self):
        """Test that pipeline correctly tracks processing statistics"""
        upload = self.create_upload_instance(self.excel_file_path)

        # Mock components to return specific statistics
        with patch(
            "data_engineering.pipelines.initial_load_pipeline.OdooExtractor"
        ) as mock_extractor_class:
            mock_extractor_instance = mock_extractor_class.return_value
            mock_extractor_instance.extract.return_value = {
                "products": pd.DataFrame({"name": ["A", "B", "C"]}),
                "sales": pd.DataFrame({"date": ["2024-01-01", "2024-01-02"]}),
            }
            mock_extractor_instance.errors = []

            with patch(
                "data_engineering.pipelines.initial_load_pipeline.OdooDataTransformer"
            ) as mock_transformer_class:
                mock_transformer_instance = mock_transformer_class.return_value
                mock_transformer_instance.transform.return_value = {
                    "transformed_data": "test"
                }
                mock_transformer_instance.errors = []
                mock_transformer_instance.warnings = []

                with patch(
                    "data_engineering.pipelines.initial_load_pipeline.RestaurantDataLoader"
                ) as mock_loader_class:
                    mock_loader_instance = mock_loader_class.return_value
                    mock_loader_instance.load.return_value = {
                        "restaurant_data": {"created": 2, "updated": 1}
                    }
                    mock_loader_instance.errors = []
                    mock_loader_instance.created_count = 2
                    mock_loader_instance.updated_count = 1
                    mock_loader_instance.error_count = 1

                    pipeline = DataProcessingPipeline(upload)
                    result = pipeline.process()

                    self.assertTrue(result)
                    self.assertEqual(upload.total_records, 5)  # 3 products + 2 sales
                    self.assertEqual(
                        upload.processed_records, 3
                    )  # 2 created + 1 updated
                    self.assertEqual(upload.error_records, 1)

                    # Check processing log contains statistics
                    self.assertIn("Total records processed: 3", upload.processing_log)
                    self.assertIn("Total errors: 1", upload.processing_log)

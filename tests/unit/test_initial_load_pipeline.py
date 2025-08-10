from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.data_management.models import DataUpload, ProcessingError
from data_engineering.pipelines.initial_load_pipeline import DataProcessingPipeline

User = get_user_model()


class TestDataProcessingPipeline(TestCase):
    """Unit tests for DataProcessingPipeline"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Create a mock file
        self.mock_file = SimpleUploadedFile(
            "test_data.xlsx",
            b"mock excel content",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # Create a DataUpload instance
        self.upload = DataUpload.objects.create(
            file=self.mock_file,
            original_file_name="test_data.xlsx",
            file_type="odoo_export",
            uploaded_by=self.user,
            status="pending",
        )

    def test_pipeline_initialization(self):
        """Test pipeline initialization with correct attributes"""
        pipeline = DataProcessingPipeline(self.upload)

        self.assertEqual(pipeline.upload, self.upload)
        self.assertEqual(pipeline.user, self.user)
        self.assertEqual(pipeline.file_path, self.upload.file.path)
        self.assertIsNone(pipeline.extractor)
        self.assertIsNone(pipeline.transformer)
        self.assertIsNone(pipeline.loader)
        self.assertEqual(pipeline.stats, {})

    @patch("data_engineering.pipelines.initial_load_pipeline.OdooExtractor")
    @patch("data_engineering.pipelines.initial_load_pipeline.OdooDataTransformer")
    @patch("data_engineering.pipelines.initial_load_pipeline.RestaurantDataLoader")
    def test_successful_pipeline_execution(
        self,
        mock_loader_class,
        mock_transformer_class,
        mock_extractor_class,
    ):
        """Test successful pipeline execution"""
        # Mock the components
        mock_extractor = Mock()
        mock_extractor.extract.return_value = {"sheet1": Mock(shape=(10, 5))}
        mock_extractor.errors = []
        mock_extractor_class.return_value = mock_extractor

        mock_transformer = Mock()
        mock_transformer.transform.return_value = {"transformed_data": "test"}
        mock_transformer.errors = []
        mock_transformer.warnings = []
        mock_transformer_class.return_value = mock_transformer

        mock_loader = Mock()
        mock_loader.load.return_value = {
            "restaurant_data": {"created": 5, "updated": 3}
        }
        mock_loader.errors = []
        mock_loader.created_count = 5
        mock_loader.updated_count = 3
        mock_loader.error_count = 0
        mock_loader_class.return_value = mock_loader

        # Execute pipeline
        pipeline = DataProcessingPipeline(self.upload)
        result = pipeline.process()

        # Assertions
        self.assertTrue(result)
        self.assertEqual(self.upload.status, "completed")
        self.assertIsNotNone(self.upload.start_processing_at)
        self.assertIsNotNone(self.upload.end_processing_at)
        self.assertEqual(self.upload.total_records, 10)
        self.assertEqual(self.upload.processed_records, 8)
        self.assertEqual(self.upload.error_records, 0)
        self.assertIn("Processing completed", self.upload.processing_log)

    @patch("data_engineering.pipelines.initial_load_pipeline.OdooExtractor")
    def test_extraction_failure(self, mock_extractor_class):
        """Test pipeline failure during extraction"""
        # Mock extractor to fail
        mock_extractor = Mock()
        mock_extractor.extract.return_value = None
        mock_extractor.errors = ["File format not supported"]
        mock_extractor_class.return_value = mock_extractor

        # Execute pipeline
        pipeline = DataProcessingPipeline(self.upload)
        result = pipeline.process()

        # Assertions
        self.assertFalse(result)
        self.assertEqual(self.upload.status, "failed")
        self.assertIn("Data extraction failed", self.upload.processing_log)
        self.assertIn("File format not supported", self.upload.processing_log)

    @patch("data_engineering.pipelines.initial_load_pipeline.OdooExtractor")
    @patch("data_engineering.pipelines.initial_load_pipeline.OdooDataTransformer")
    def test_transformation_failure(self, mock_transformer_class, mock_extractor_class):
        """Test pipeline failure during transformation"""
        # Mock extractor to succeed
        mock_extractor = Mock()
        mock_extractor.extract.return_value = {"sheet1": Mock(shape=(5, 3))}
        mock_extractor.errors = []
        mock_extractor_class.return_value = mock_extractor

        # Mock transformer to fail
        mock_transformer = Mock()
        mock_transformer.transform.return_value = None
        mock_transformer.errors = ["Invalid data format"]
        mock_transformer_class.return_value = mock_transformer

        # Execute pipeline
        pipeline = DataProcessingPipeline(self.upload)
        result = pipeline.process()

        # Assertions
        self.assertFalse(result)
        self.assertEqual(self.upload.status, "failed")
        self.assertIn("Data transformation failed", self.upload.processing_log)

    @patch("data_engineering.pipelines.initial_load_pipeline.OdooExtractor")
    @patch("data_engineering.pipelines.initial_load_pipeline.OdooDataTransformer")
    @patch("data_engineering.pipelines.initial_load_pipeline.RestaurantDataLoader")
    def test_loading_failure(
        self, mock_loader_class, mock_transformer_class, mock_extractor_class
    ):
        """Test pipeline failure during loading"""
        # Mock extractor and transformer to succeed
        mock_extractor = Mock()
        mock_extractor.extract.return_value = {"sheet1": Mock(shape=(5, 3))}
        mock_extractor.errors = []
        mock_extractor_class.return_value = mock_extractor

        mock_transformer = Mock()
        mock_transformer.transform.return_value = {"transformed_data": "test"}
        mock_transformer.errors = []
        mock_transformer.warnings = []
        mock_transformer_class.return_value = mock_transformer

        # Mock loader to fail
        mock_loader = Mock()
        mock_loader.load.return_value = None
        mock_loader.errors = ["Database connection failed"]
        mock_loader_class.return_value = mock_loader

        # Execute pipeline
        pipeline = DataProcessingPipeline(self.upload)
        result = pipeline.process()

        # Assertions
        self.assertFalse(result)
        self.assertEqual(self.upload.status, "failed")
        self.assertIn("Data loading failed", self.upload.processing_log)

    def test_extract_data_with_odoo_export(self):
        """Test data extraction for Odoo export files"""
        with patch(
            "data_engineering.pipelines.initial_load_pipeline.OdooExtractor"
        ) as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor.extract.return_value = {
                "products": Mock(shape=(10, 5)),
                "sales": Mock(shape=(15, 4)),
            }
            mock_extractor.errors = []
            mock_extractor_class.return_value = mock_extractor

            pipeline = DataProcessingPipeline(self.upload)
            result = pipeline._extract_data()

            self.assertIsNotNone(result)
            self.assertEqual(self.upload.total_records, 25)
            mock_extractor_class.assert_called_once_with(self.upload.file.path)

    def test_extract_data_with_recipes_data(self):
        """Test data extraction for recipes data files"""
        self.upload.file_type = "recipes_data"
        self.upload.save()

        with patch(
            "data_engineering.pipelines.initial_load_pipeline.RecipeExtractor"
        ) as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor.extract.return_value = {"recipes": Mock(shape=(8, 6))}
            mock_extractor.errors = []
            mock_extractor_class.return_value = mock_extractor

            pipeline = DataProcessingPipeline(self.upload)
            result = pipeline._extract_data()

            self.assertIsNotNone(result)
            self.assertEqual(self.upload.total_records, 8)
            mock_extractor_class.assert_called_once_with(self.upload.file.path)

    def test_extract_data_with_extraction_errors(self):
        """Test data extraction with errors"""
        with patch(
            "data_engineering.pipelines.initial_load_pipeline.OdooExtractor"
        ) as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor.extract.return_value = None
            mock_extractor.errors = ["Invalid file format", "Missing required columns"]
            mock_extractor_class.return_value = mock_extractor

            pipeline = DataProcessingPipeline(self.upload)
            result = pipeline._extract_data()

            self.assertIsNone(result)
            # Check that processing errors were created
            errors = ProcessingError.objects.filter(upload=self.upload)
            self.assertEqual(errors.count(), 2)

    def test_transform_data_with_odoo_export(self):
        """Test data transformation for Odoo export files"""
        extracted_data = {"products": Mock(), "sales": Mock()}

        with patch(
            "data_engineering.pipelines.initial_load_pipeline.OdooDataTransformer"
        ) as mock_transformer_class:
            mock_transformer = Mock()
            mock_transformer.transform.return_value = {"transformed_products": "data"}
            mock_transformer.errors = []
            mock_transformer.warnings = ["Some data was cleaned"]
            mock_transformer_class.return_value = mock_transformer

            pipeline = DataProcessingPipeline(self.upload)
            result = pipeline._transform_data(extracted_data)

            self.assertIsNotNone(result)
            mock_transformer_class.assert_called_once_with(user=self.user)

    def test_transform_data_with_recipes_data(self):
        """Test data transformation for recipes data files"""
        self.upload.file_type = "recipes_data"
        self.upload.save()

        extracted_data = {"recipes": Mock()}

        with patch(
            "data_engineering.pipelines.initial_load_pipeline.RecipeDataTransformer"
        ) as mock_transformer_class:
            mock_transformer = Mock()
            mock_transformer.transform.return_value = {"transformed_recipes": "data"}
            mock_transformer.errors = []
            mock_transformer.warnings = []
            mock_transformer_class.return_value = mock_transformer

            pipeline = DataProcessingPipeline(self.upload)
            result = pipeline._transform_data(extracted_data)

            self.assertIsNotNone(result)
            mock_transformer_class.assert_called_once_with(user=self.user)

    def test_load_data_with_odoo_export(self):
        """Test data loading for Odoo export files"""
        transformed_data = {"transformed_products": "data"}

        with patch(
            "data_engineering.pipelines.initial_load_pipeline.RestaurantDataLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_loader.load.return_value = {"restaurant_data": {"created": 10}}
            mock_loader.errors = []
            mock_loader.created_count = 10
            mock_loader.updated_count = 0
            mock_loader.error_count = 0
            mock_loader_class.return_value = mock_loader

            pipeline = DataProcessingPipeline(self.upload)
            result = pipeline._load_data(transformed_data)

            self.assertIsNotNone(result)
            self.assertEqual(self.upload.processed_records, 10)
            self.assertEqual(self.upload.error_records, 0)
            mock_loader_class.assert_called_once_with(
                self.user, upload_instance=self.upload
            )

    def test_load_data_with_recipes_data(self):
        """Test data loading for recipes data files"""
        self.upload.file_type = "recipes_data"
        self.upload.save()

        transformed_data = {"transformed_recipes": "data"}

        with patch(
            "data_engineering.pipelines.initial_load_pipeline.RecipeDataLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_loader.load.return_value = {
                "recipe_data": {"created": 5, "updated": 2}
            }
            mock_loader.errors = []
            mock_loader.created_count = 5
            mock_loader.updated_count = 2
            mock_loader.error_count = 1
            mock_loader_class.return_value = mock_loader

            pipeline = DataProcessingPipeline(self.upload)
            result = pipeline._load_data(transformed_data)

            self.assertIsNotNone(result)
            self.assertEqual(self.upload.processed_records, 7)  # 5 created + 2 updated
            self.assertEqual(self.upload.error_records, 1)
            mock_loader_class.assert_called_once_with(
                self.user, upload_instance=self.upload
            )

    def test_handle_success(self):
        """Test successful pipeline completion handling"""
        load_results = {
            "restaurant_data": {"created": 10, "updated": 5},
            "product_data": {"created": 3, "updated": 2},
        }

        quality_metrics = {
            "products": {"quality_score": 85.0, "total_issues": 5},
            "sales": {"quality_score": 90.0, "total_issues": 3},
        }

        pipeline = DataProcessingPipeline(self.upload)
        pipeline._handle_success(load_results, quality_metrics)

        self.assertEqual(self.upload.status, "completed")
        self.assertIsNotNone(self.upload.end_processing_at)
        self.assertIn("Processing completed", self.upload.processing_log)
        self.assertIn("Restaurant_data", self.upload.processing_log)
        self.assertIn("Product_data", self.upload.processing_log)

    def test_handle_error(self):
        """Test error handling"""
        error_msg = "Test error message"

        pipeline = DataProcessingPipeline(self.upload)
        pipeline._handle_error(error_msg)

        self.assertEqual(self.upload.status, "failed")
        self.assertIsNotNone(self.upload.end_processing_at)
        self.assertIn("Processing failed", self.upload.processing_log)
        self.assertIn(error_msg, self.upload.processing_log)

    def test_log_processing_error(self):
        """Test logging of individual processing errors"""
        pipeline = DataProcessingPipeline(self.upload)
        pipeline._log_processing_error(5, "validation", "Invalid data in row 5")

        error = ProcessingError.objects.get(upload=self.upload)
        self.assertEqual(error.row_number, 5)
        self.assertEqual(error.error_type, "validation")
        self.assertEqual(error.error_message, "Invalid data in row 5")

    def test_pipeline_with_exception(self):
        """Test pipeline behavior when an exception occurs"""
        with patch(
            "data_engineering.pipelines.initial_load_pipeline.OdooExtractor"
        ) as mock_extractor_class:
            mock_extractor_class.side_effect = Exception("Unexpected error")

            pipeline = DataProcessingPipeline(self.upload)
            result = pipeline.process()

            self.assertFalse(result)
            self.assertEqual(self.upload.status, "failed")
            self.assertIn("Data extraction failed", self.upload.processing_log)

    def test_pipeline_status_updates(self):
        """Test that pipeline correctly updates upload status throughout processing"""
        with patch(
            "data_engineering.pipelines.initial_load_pipeline.OdooExtractor"
        ) as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor.extract.return_value = {"sheet1": Mock(shape=(5, 3))}
            mock_extractor.errors = []
            mock_extractor_class.return_value = mock_extractor

            with patch(
                "data_engineering.pipelines.initial_load_pipeline.OdooDataTransformer"
            ) as mock_transformer_class:
                mock_transformer = Mock()
                mock_transformer.transform.return_value = {"transformed_data": "test"}
                mock_transformer.errors = []
                mock_transformer.warnings = []
                mock_transformer_class.return_value = mock_transformer

                # NOTE: Consolidation no longer done in pipeline
                with patch(
                    "data_engineering.pipelines.initial_load_pipeline.RestaurantDataLoader"
                ) as mock_loader_class:
                    mock_loader = Mock()
                    mock_loader.load.return_value = {"restaurant_data": {"created": 5}}
                    mock_loader.errors = []
                    mock_loader.created_count = 5
                    mock_loader.updated_count = 0
                    mock_loader.error_count = 0
                    mock_loader_class.return_value = mock_loader

                    pipeline = DataProcessingPipeline(self.upload)

                    # Check initial status
                    self.assertEqual(self.upload.status, "pending")

                    # Run pipeline
                    result = pipeline.process()

                    # Check final status
                    self.assertTrue(result)
                    self.assertEqual(self.upload.status, "completed")
                    self.assertIsNotNone(self.upload.start_processing_at)
                    self.assertIsNotNone(self.upload.end_processing_at)

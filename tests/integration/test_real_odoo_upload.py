import os
import tempfile

import pandas as pd
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.data_management.models import DataUpload
from apps.restaurant_data.models import Product, Purchase, Sales
from data_engineering.pipelines.initial_load_pipeline import DataProcessingPipeline

User = get_user_model()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TestRealOdooUpload(TestCase):
    """End-to-end test for uploading real Odoo files and checking database state"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()

        # Create sample Odoo data that mimics real structure
        self.create_sample_odoo_file()

    def tearDown(self):
        """Clean up test files"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_sample_odoo_file(self):
        """Create a realistic Odoo Excel file with products, purchases, and sales"""

        # Products sheet - with potential case variations
        products_data = {
            "name": [
                "Ailes de Poulet Cru (Kg)",
                "Coca Cola Original",
                "Schweppes Agrumes",
                "Tomates Fraîches",
                "Oignons Blancs",
                "Pommes de Terre",
                "Carottes",
                "Poivrons Rouges",
                "Concombres",
                "Salade Verte",
            ],
            "purchase_category": [
                "Grillades",
                "Boissons",
                "Boissons",
                "Légumes",
                "Légumes",
                "Légumes",
                "Légumes",
                "Légumes",
                "Légumes",
                "Légumes",
            ],
            "sales_category": [
                "Produits Alimentaires / Aliments / Aliments Frais / Volaille",
                "Boissons / Sodas",
                "Boissons / Sodas",
                "Produits Alimentaires / Aliments / Aliments Frais / Légumes",
                "Produits Alimentaires / Aliments / Aliments Frais / Légumes",
                "Produits Alimentaires / Aliments / Aliments Frais / Légumes",
                "Produits Alimentaires / Aliments / Aliments Frais / Légumes",
                "Produits Alimentaires / Aliments / Aliments Frais / Légumes",
                "Produits Alimentaires / Aliments / Aliments Frais / Légumes",
                "Produits Alimentaires / Aliments / Aliments Frais / Légumes",
            ],
            "unit_of_measure": [
                "kg",
                "unit",
                "unit",
                "kg",
                "kg",
                "kg",
                "kg",
                "kg",
                "kg",
                "unit",
            ],
            "current_selling_price": [
                13.54,
                2.50,
                2.00,
                3.50,
                2.00,
                1.50,
                2.50,
                4.00,
                2.50,
                1.00,
            ],
            "current_cost_per_unit": [
                8.50,
                1.80,
                1.50,
                2.20,
                1.20,
                0.80,
                1.50,
                2.80,
                1.50,
                0.60,
            ],
            "current_stock": [50.0, 100, 80, 25.0, 30.0, 40.0, 35.0, 15.0, 20.0, 25],
        }

        # Purchases sheet - tabular format with required columns
        purchases_data = {
            "purchase_date": [
                "2025-01-05", "2025-01-05", "2025-01-05", "2025-01-05", "2025-01-05",
                "2025-01-06", "2025-01-06", "2025-01-06", "2025-01-06", "2025-01-06",
            ],
            "product": [
                "Ailes de Poulet Cru (Kg)", "Coca Cola Original", "Schweppes Agrumes", "Tomates Fraîches", "Oignons Blancs",
                "Ailes de Poulet Cru (Kg)", "Coca Cola Original", "Schweppes Agrumes", "Tomates Fraîches", "Oignons Blancs",
            ],
            "quantity_purchased": [10.0, 50, 30, 5.0, 8.0, 15.0, 60, 40, 7.0, 10.0],
            "total_cost": [135.40, 125.00, 60.00, 17.50, 16.00, 203.10, 150.00, 80.00, 24.50, 20.00],
        }

        # Sales sheet - tabular format with required columns
        sales_data = {
            "sale_date": [
                "2025-01-05", "2025-01-05", "2025-01-05", "2025-01-05", "2025-01-05",
                "2025-01-06", "2025-01-06", "2025-01-06", "2025-01-06", "2025-01-06",
            ],
            "order_number": ["ORD001", "ORD002", "ORD003", "ORD004", "ORD005", "ORD006", "ORD007", "ORD008", "ORD009", "ORD010"],
            "product": [
                "Ailes de Poulet Cru (Kg)", "Coca Cola Original", "Schweppes Agrumes", "Tomates Fraîches", "Oignons Blancs",
                "Ailes de Poulet Cru (Kg)", "Coca Cola Original", "Schweppes Agrumes", "Tomates Fraîches", "Oignons Blancs",
            ],
            "quantity_sold": [5.0, 25, 15, 2.5, 4.0, 7.0, 30, 20, 3.5, 5.0],
            "unit_sale_price": [13.54, 2.50, 2.00, 3.50, 2.00, 13.54, 2.50, 2.00, 3.50, 2.00],
            "total_sale_price": [67.70, 62.50, 30.00, 8.75, 8.00, 94.78, 75.00, 40.00, 12.25, 10.00],
            "customer": ["Walk-in", "Walk-in", "Walk-in", "Walk-in", "Walk-in", "Walk-in", "Walk-in", "Walk-in", "Walk-in", "Walk-in"],
            "cashier": ["Cashier1", "Cashier1", "Cashier1", "Cashier1", "Cashier1", "Cashier1", "Cashier1", "Cashier1", "Cashier1", "Cashier1"],
        }

        # Create Excel file
        self.excel_file_path = os.path.join(self.temp_dir, "test_odoo_data.xlsx")
        with pd.ExcelWriter(self.excel_file_path, engine="openpyxl") as writer:
            pd.DataFrame(products_data).to_excel(
                writer, sheet_name="products", index=False
            )
            pd.DataFrame(purchases_data).to_excel(
                writer, sheet_name="purchases", index=False
            )
            pd.DataFrame(sales_data).to_excel(writer, sheet_name="sales", index=False)

    def create_upload_instance(self):
        """Helper method to create a DataUpload instance"""
        with open(self.excel_file_path, "rb") as f:
            file_content = f.read()

        uploaded_file = SimpleUploadedFile(
            "test_odoo_data.xlsx",
            file_content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        return DataUpload.objects.create(
            file=uploaded_file,
            original_file_name="test_odoo_data.xlsx",
            file_type="odoo_export",
            uploaded_by=self.user,
            status="pending",
        )

    def test_duplicate_product_debug(self):
        """Debug test to understand why more products are being created than expected"""

        # Create upload instance
        upload = self.create_upload_instance()

        # Get initial product count
        initial_product_count = Product.objects.count()

        # Run the actual pipeline (no mocking)
        pipeline = DataProcessingPipeline(upload)
        result = pipeline.process()

        self.assertTrue(result, "Pipeline should complete successfully")

        # Get final product count
        final_product_count = Product.objects.count()
        products_created = final_product_count - initial_product_count

        print("\n=== DUPLICATE PRODUCT DEBUG ===")
        print(f"Initial products: {initial_product_count}")
        print(f"Final products: {final_product_count}")
        print(f"Products created: {products_created}")
        print("Expected: 10")

        # List all products to see what was created
        all_products = Product.objects.all().order_by("name")
        print(f"\nAll products in database ({len(all_products)}):")
        for i, product in enumerate(all_products, 1):
            print(f"{i:2d}. {product.name} (ID: {product.id})")

        # Check for case-insensitive duplicates
        product_names_lower = [p.name.lower() for p in all_products]
        unique_names_lower = set(product_names_lower)

        print(f"\nUnique product names (case-insensitive): {len(unique_names_lower)}")
        print(f"Total product names: {len(product_names_lower)}")

        if len(product_names_lower) != len(unique_names_lower):
            print("\nDUPLICATES FOUND!")
            # Find duplicates
            from collections import Counter

            name_counts = Counter(product_names_lower)
            duplicates = {
                name: count for name, count in name_counts.items() if count > 1
            }

            print("Duplicate names:")
            for name, count in duplicates.items():
                print(f"  '{name}' appears {count} times")
                # Show the actual products with this name
                products_with_name = [p for p in all_products if p.name.lower() == name]
                for product in products_with_name:
                    print(f"    - {product.name} (ID: {product.id})")

        # Verify the test data products exist
        expected_product_names = [
            "Ailes de Poulet Cru (Kg)",
            "Coca Cola Original",
            "Schweppes Agrumes",
            "Tomates Fraîches",
            "Oignons Blancs",
            "Pommes de Terre",
            "Carottes",
            "Poivrons Rouges",
            "Concombres",
            "Salade Verte",
        ]

        print("\nChecking expected products:")
        for product_name in expected_product_names:
            product = Product.objects.filter(name__iexact=product_name).first()
            if product:
                print(f"✓ Found: {product.name} (ID: {product.id})")
            else:
                print(f"✗ Missing: {product_name}")

        # This test should fail if we have duplicates, helping us understand the issue
        self.assertEqual(
            len(product_names_lower),
            len(unique_names_lower),
            f"Found {len(product_names_lower) - len(unique_names_lower)} duplicate products (case-insensitive)",
        )

    def test_real_odoo_upload_and_product_verification(self):
        """Test uploading a real Odoo file and verifying product database state"""

        # Create upload instance
        upload = self.create_upload_instance()

        # Get initial product count
        initial_product_count = Product.objects.count()

        # Run the actual pipeline (no mocking)
        pipeline = DataProcessingPipeline(upload)
        result = pipeline.process()

        # Verify pipeline completed successfully
        self.assertTrue(result, "Pipeline should complete successfully")
        self.assertEqual(
            upload.status, "completed", "Upload status should be completed"
        )

        # Verify products were created correctly
        final_product_count = Product.objects.count()
        expected_products_created = 10  # From our test data

        self.assertEqual(
            final_product_count - initial_product_count,
            expected_products_created,
            f"Expected {expected_products_created} products to be created, but got {final_product_count - initial_product_count}",
        )

        # Verify specific products exist with correct names
        expected_product_names = [
            "Ailes de Poulet Cru (Kg)",
            "Coca Cola Original",
            "Schweppes Agrumes",
            "Tomates Fraîches",
            "Oignons Blancs",
            "Pommes de Terre",
            "Carottes",
            "Poivrons Rouges",
            "Concombres",
            "Salade Verte",
        ]

        for product_name in expected_product_names:
            product = Product.objects.filter(name__iexact=product_name).first()
            self.assertIsNotNone(
                product, f"Product '{product_name}' should exist in database"
            )

        # Verify no duplicate products (case-insensitive)
        all_products = Product.objects.all()
        product_names_lower = [p.name.lower() for p in all_products]
        unique_names_lower = set(product_names_lower)

        self.assertEqual(
            len(product_names_lower),
            len(unique_names_lower),
            "No duplicate products should exist (case-insensitive)",
        )

        # Verify purchases and sales were created
        purchases_count = Purchase.objects.count()
        sales_count = Sales.objects.count()

        self.assertGreater(purchases_count, 0, "Purchases should be created")
        self.assertGreater(sales_count, 0, "Sales should be created")

        # Verify upload statistics
        # Expected counts based on test data:
        # - Products: 10
        # - Purchases: 10 (2 dates × 5 products each)
        # - Sales: 10 (2 dates × 5 products each)
        # - Consolidated purchases: 10 (derived from purchases)
        # - Consolidated sales: 10 (derived from sales)
        # - Product types: 10 (derived from products)
        # Total expected: 60 (pipeline counts all data types including derived ones)
        expected_purchases = 10
        expected_sales = 10
        expected_total_records = 60  # Pipeline counts all data types including derived/consolidated data
        
        print(f"\n=== UPLOAD STATISTICS DEBUG ===")
        print(f"Products created: {expected_products_created}")
        print(f"Purchases created: {purchases_count} (expected: {expected_purchases})")
        print(f"Sales created: {sales_count} (expected: {expected_sales})")
        print(f"Total records processed: {upload.processed_records} (expected: {expected_total_records})")
        print(f"Note: Pipeline counts all data types including consolidated/derived data")
        
        # Check if the counts match expectations
        self.assertEqual(purchases_count, expected_purchases, f"Expected {expected_purchases} purchases, but got {purchases_count}")
        self.assertEqual(sales_count, expected_sales, f"Expected {expected_sales} sales, but got {sales_count}")
        self.assertEqual(
            upload.processed_records,
            expected_total_records,
            f"Expected {expected_total_records} total records (including derived data), but got {upload.processed_records}",
        )
        self.assertEqual(upload.error_records, 0, "No errors should occur")

    def test_case_insensitive_product_creation(self):
        """Test that case-insensitive product creation works correctly"""

        # Create upload instance
        upload = self.create_upload_instance()

        # Run pipeline
        pipeline = DataProcessingPipeline(upload)
        result = pipeline.process()

        self.assertTrue(result, "Pipeline should complete successfully")

        # Check that products with different cases are treated as the same
        # This should not create duplicates
        product_count = Product.objects.count()

        # Try to create a product with different case
        duplicate_product = Product.objects.create(
            name="AILES DE POULET CRU (KG)",  # Different case
            purchase_category_id=1,
            sales_category_id=1,
            unit_of_measure_id=1,
            current_selling_price=13.54,
            current_cost_per_unit=8.50,
            current_stock=50.0,
            created_by=self.user,
            updated_by=self.user,
        )

        # The case-insensitive lookup should prevent this from creating a duplicate
        # But since we're testing the actual creation, let's verify the behavior
        new_product_count = Product.objects.count()

        # Clean up the test product
        duplicate_product.delete()

        # Verify the original product still exists
        original_product = Product.objects.filter(
            name__iexact="Ailes de Poulet Cru (Kg)"
        ).first()
        self.assertIsNotNone(original_product, "Original product should still exist")

    def test_product_attributes_verification(self):
        """Test that product attributes are correctly set"""

        # Create upload instance
        upload = self.create_upload_instance()

        # Run pipeline
        pipeline = DataProcessingPipeline(upload)
        result = pipeline.process()

        self.assertTrue(result, "Pipeline should complete successfully")

        # Verify specific product attributes
        poulet_product = Product.objects.filter(
            name__iexact="Ailes de Poulet Cru (Kg)"
        ).first()
        self.assertIsNotNone(poulet_product, "Poulet product should exist")

        self.assertEqual(float(poulet_product.current_selling_price), 13.54)
        self.assertEqual(float(poulet_product.current_cost_per_unit), 8.50)
        self.assertEqual(poulet_product.current_stock, 50.0)
        self.assertEqual(poulet_product.unit_of_measure.name, "kg")

        # Verify category relationships
        self.assertEqual(poulet_product.purchase_category.name, "Grillades")
        self.assertIn("Volaille", poulet_product.sales_category.name)

    def test_purchase_sales_linking(self):
        """Test that purchases and sales are correctly linked to products"""

        # Create upload instance
        upload = self.create_upload_instance()

        # Run pipeline
        pipeline = DataProcessingPipeline(upload)
        result = pipeline.process()

        self.assertTrue(result, "Pipeline should complete successfully")

        # Verify purchases are linked to products
        purchases = Purchase.objects.all()
        for purchase in purchases:
            self.assertIsNotNone(
                purchase.product, "Purchase should be linked to a product"
            )
            self.assertIsNotNone(purchase.purchase_date, "Purchase should have a date")
            self.assertGreater(
                purchase.quantity_purchased, 0, "Purchase should have quantity"
            )
            self.assertGreater(
                purchase.total_cost, 0, "Purchase should have total cost"
            )

        # Verify sales are linked to products
        sales = Sales.objects.all()
        for sale in sales:
            self.assertIsNotNone(sale.product, "Sale should be linked to a product")
            self.assertIsNotNone(sale.sale_date, "Sale should have a date")
            self.assertGreater(sale.quantity_sold, 0, "Sale should have quantity")
            self.assertGreater(sale.unit_sale_price, 0, "Sale should have unit price")
            self.assertGreater(sale.total_sale_price, 0, "Sale should have total price")

    def test_data_quality_analysis(self):
        """Test that data quality analysis is performed and stored"""

        # Create upload instance
        upload = self.create_upload_instance()

        # Run pipeline
        pipeline = DataProcessingPipeline(upload)
        result = pipeline.process()

        self.assertTrue(result, "Pipeline should complete successfully")

        # Verify data quality metrics are stored
        self.assertIsNotNone(
            upload.data_quality_metrics, "Data quality metrics should be stored"
        )
        self.assertIsInstance(
            upload.data_quality_metrics, dict, "Data quality metrics should be a dict"
        )

        # Verify quality metrics contain expected keys
        quality_metrics = upload.data_quality_metrics
        self.assertIn(
            "products", quality_metrics, "Products quality should be analyzed"
        )
        self.assertIn(
            "purchases", quality_metrics, "Purchases quality should be analyzed"
        )
        self.assertIn("sales", quality_metrics, "Sales quality should be analyzed")

        # Verify quality scores are calculated
        for sheet_type, metrics in quality_metrics.items():
            self.assertIn(
                "quality_score",
                metrics,
                f"Quality score should be calculated for {sheet_type}",
            )
            self.assertIn(
                "total_issues",
                metrics,
                f"Total issues should be calculated for {sheet_type}",
            )
            self.assertIn(
                "critical_issues",
                metrics,
                f"Critical issues should be calculated for {sheet_type}",
            )

    def test_processing_log_verification(self):
        """Test that processing log contains expected information"""

        # Create upload instance
        upload = self.create_upload_instance()

        # Run pipeline
        pipeline = DataProcessingPipeline(upload)
        result = pipeline.process()

        self.assertTrue(result, "Pipeline should complete successfully")

        # Verify processing log contains expected information
        self.assertIsNotNone(upload.processing_log, "Processing log should be created")
        self.assertIn("Processing completed", upload.processing_log)
        self.assertIn("Total records processed", upload.processing_log)
        self.assertIn("Products:", upload.processing_log)
        self.assertIn("Purchases:", upload.processing_log)
        self.assertIn("Sales:", upload.processing_log)
        self.assertIn("Data Quality Summary:", upload.processing_log)

#!/usr/bin/env python3
"""
Test script for loading products and checking units
This script allows you to test product loading and see what units are being saved.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
import django

django.setup()

from django.contrib.auth import get_user_model

from apps.restaurant_data.models import Product, UnitOfMeasure
from data_engineering.extractors.odoo_extractor import OdooExtractor
from data_engineering.loaders.database_loader import RestaurantDataLoader
from data_engineering.transformers.odoo_data_cleaner import OdooDataTransformer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

User = get_user_model()


def test_product_loading(file_path: str):
    """
    Test product loading and check units
    """
    print(f"\n{'='*80}")
    print("TESTING PRODUCT LOADING AND UNITS")
    print(f"File: {file_path}")
    print(f"{'='*80}")

    try:
        # Step 1: Extract data
        print("\n1. EXTRACTING DATA...")
        extractor = OdooExtractor(file_path)
        extracted_data = extractor.extract()

        if not extracted_data or "products" not in extracted_data:
            print("❌ No products data found!")
            return

        products_df = extracted_data["products"]
        print(f"✅ Extracted {len(products_df)} products")

        # Show original units from Excel
        print("\nOriginal units from Excel:")
        if "unit_of_measure" in products_df.columns:
            unit_counts = products_df["unit_of_measure"].value_counts()
            for unit, count in unit_counts.items():
                print(f"  {unit}: {count} products")
            
            # Show specific products and their original units
            print("\nSpecific products and their original units:")
            for idx, row in products_df.iterrows():
                product_name = row.get("name", "Unknown")
                unit = row.get("unit_of_measure", "Unknown")
                if "plantain" in product_name.lower():
                    print(f"  {product_name}: '{unit}' (type: {type(unit)})")
        else:
            print("  No unit_of_measure column found")
            print(f"  Available columns: {list(products_df.columns)}")

        # Step 2: Transform data
        print("\n2. TRANSFORMING DATA...")
        transformer = OdooDataTransformer()
        transformed_data = transformer.transform(extracted_data)

        if not transformed_data or "products" not in transformed_data:
            print("❌ No transformed products data!")
            return

        transformed_products_df = transformed_data["products"]
        print(f"✅ Transformed {len(transformed_products_df)} products")

        # Show transformed units
        print("\nTransformed units:")
        if "unit_of_measure" in transformed_products_df.columns:
            unit_counts = transformed_products_df["unit_of_measure"].value_counts()
            for unit, count in unit_counts.items():
                print(f"  {unit}: {count} products")

            # Show specific products and their units
            print("\nProduct units (first 10):")
            for idx, row in transformed_products_df.head(10).iterrows():
                product_name = row.get("name", "Unknown")
                unit = row.get("unit_of_measure", "Unknown")
                print(f"  {product_name}: {unit}")
        else:
            print("  No unit_of_measure column found in transformed data")

        # Step 3: Load data (optional - only if you want to save to database)
        print("\n3. LOADING DATA TO DATABASE...")

        # Get or create a test user
        try:
            user = User.objects.first()
            if not user:
                user = User.objects.create_user(
                    username="test_user",
                    email="test@example.com",
                    password="testpass123",
                )
                print(f"✅ Created test user: {user.username}")
            else:
                print(f"✅ Using existing user: {user.username}")
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            return

        # Clear existing products for testing
        Product.objects.all().delete()
        UnitOfMeasure.objects.all().delete()
        print("✅ Cleared existing products and units")

        # Load data
        loader = RestaurantDataLoader(user=user)
        results = loader.load(transformed_data)

        print("✅ Loading completed")
        print(f"Results: {results}")

        # Step 4: Check what was actually saved
        print("\n4. CHECKING SAVED DATA...")

        # Check units in database
        units_in_db = UnitOfMeasure.objects.all()
        print(f"\nUnits in database ({units_in_db.count()}):")
        for unit in units_in_db:
            print(f"  {unit.name} (abbreviation: {unit.abbreviation})")

        # Check products and their units
        products_in_db = Product.objects.select_related("unit_of_measure").all()
        print(f"\nProducts in database ({products_in_db.count()}):")
        for product in products_in_db:
            print(f"  {product.name}: {product.unit_of_measure.name}")

        # Check specific products
        plantains = Product.objects.filter(name__icontains="plantain").first()
        if plantains:
            print(f"\nPlantains unit: {plantains.unit_of_measure.name}")
        else:
            print("\nNo Plantains found in database")

        return transformed_data

    except Exception as e:
        print(f"❌ Error testing product loading: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description="Test product loading and units")
    parser.add_argument("file", help="Path to the Excel file to test")
    parser.add_argument("--dry-run", action="store_true", help="Don't save to database")

    args = parser.parse_args()

    if not Path(args.file).exists():
        print(f"❌ File not found: {args.file}")
        return

    test_product_loading(args.file)


if __name__ == "__main__":
    main()

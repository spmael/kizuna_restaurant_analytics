#!/usr/bin/env python
"""
Test script for product consolidation functionality
"""

import os
import sys
from decimal import Decimal

import django
import pandas as pd

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.restaurant_data.models import ProductConsolidation
from data_engineering.utils.product_consolidation import ProductConsolidationService


def test_consolidation_transformer():
    """Test the consolidation transformer with sample data"""

    print("Testing Product Consolidation Transformer...")

    # Create sample data
    sample_data = {
        "purchases": pd.DataFrame(
            {
                "product": [
                    "Poulet Cru (Kg)",
                    "Ailes de Poulet Cru (Kg)",
                    "Filet de Bœuf",
                    "Pomme de terre Allumettes",
                    "Mayonnaise ARMANTI",
                    "Huile de tournesol",
                    "Product Not in Rules",
                ],
                "quantity_purchased": [1, 2, 3, 4, 5, 6, 7],
                "total_cost": [10, 20, 30, 40, 50, 60, 70],
            }
        )
    }

    print(f"Sample data created with {len(sample_data['purchases'])} records")

    # Initialize service
    service = ProductConsolidationService()

    # Test rule creation
    try:
        # This script would need to be updated for the new architecture transformer.transform(sample_data)

        print("\nTransformation completed successfully!")
        print(f"Transformed data shape: {transformed_data['purchases'].shape}")

        # Show results
        print("\nConsolidation Results:")
        df = transformed_data["purchases"]

        for idx, row in df.iterrows():
            original = row["original_product_name"]
            consolidated = row["product"]
            applied = row["consolidation_applied"]

            if applied:
                print(f"  {original} → {consolidated}")
            else:
                print(f"  {original} (no consolidation)")

        # Show statistics
        consolidations_applied = df["consolidation_applied"].sum()
        print("\nStatistics:")
        print(f"  Total records: {len(df)}")
        print(f"  Consolidations applied: {consolidations_applied}")
        print(f"  Consolidation rate: {consolidations_applied/len(df)*100:.1f}%")

        return True

    except Exception as e:
        print(f"❌ Error during transformation: {str(e)}")
        return False


def test_consolidation_rule_creation():
    """Test creating consolidation rules"""

    print("\nTesting Consolidation Rule Creation...")

    try:
        transformer = ProductConsolidationTransformer()

        # Create a test consolidation rule
        consolidation = transformer.create_consolidation_rule(
            primary_product_name="Test Primary Product",
            consolidated_product_names=["Test Product 1", "Test Product 2"],
            consolidation_reason="test_consolidation",
            confidence_score=Decimal("0.85"),
            notes="Test consolidation rule",
        )

        print(f"Created consolidation rule with ID: {consolidation.id}")
        print(f"   Primary product: {consolidation.primary_product.name}")
        print(f"   Consolidated products: {len(consolidation.consolidated_products)}")
        print(f"   Confidence: {consolidation.confidence_score}")

        # Clean up - delete the test rule
        consolidation.delete()
        print("Test consolidation rule cleaned up")

        return True

    except Exception as e:
        print(f"❌ Error creating consolidation rule: {str(e)}")
        return False


def check_existing_consolidations():
    """Check existing consolidation rules in the database"""

    print("\nChecking Existing Consolidation Rules...")

    try:
        consolidations = ProductConsolidation.objects.all()

        if consolidations.exists():
            print(f"Found {consolidations.count()} consolidation rules:")

            for consolidation in consolidations:
                print(
                    f"  • {consolidation.primary_product.name} (ID: {consolidation.id})"
                )
                print(
                    f"    - Consolidates {len(consolidation.consolidated_products)} products"
                )
                print(f"    - Reason: {consolidation.consolidation_reason}")
                print(f"    - Confidence: {consolidation.confidence_score}")
                print(f"    - Verified: {consolidation.is_verified}")
                print()
        else:
            print("No consolidation rules found in database")
            print(
                "Run 'python manage.py load_legacy_consolidation_rules' to load legacy rules"
            )

        return True

    except Exception as e:
        print(f"❌ Error checking consolidations: {str(e)}")
        return False


def main():
    """Run all tests"""

    print("Starting Product Consolidation Tests...\n")

    # Check existing consolidations
    check_existing_consolidations()

    # Test rule creation
    test_consolidation_rule_creation()

    # Test transformer
    test_consolidation_transformer()

    print("\nAll tests completed!")


if __name__ == "__main__":
    main()

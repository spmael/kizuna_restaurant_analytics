#!/usr/bin/env python3
"""
Script to remove wrong unit conversions for products that get consolidated
"""

import os
import sys

import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.restaurant_data.models import UnitConversion, UnitOfMeasure
from data_engineering.utils.product_consolidation import ProductConsolidationService


def cleanup_wrong_conversions():
    print("=== Cleaning Up Wrong Unit Conversions ===\n")

    consolidation_service = ProductConsolidationService()
    unit_measure = UnitOfMeasure.objects.filter(name="unit").first()
    g_measure = UnitOfMeasure.objects.filter(name="g").first()

    if not unit_measure or not g_measure:
        print("❌ Unit measures not found!")
        return

    # Find all unit→g conversions
    conversions = UnitConversion.objects.filter(
        from_unit=unit_measure, to_unit=g_measure
    )

    print(f"Found {conversions.count()} unit→g conversions")

    removed_count = 0
    for conversion in conversions:
        if conversion.product:
            # Check if this product gets consolidated to a different product
            consolidated_product = consolidation_service.find_consolidated_product(
                conversion.product.name
            )

            if (
                consolidated_product
                and consolidated_product.id != conversion.product.id
            ):
                print(
                    f"❌ Removing wrong conversion: {conversion.product.name} → {conversion.conversion_factor}g"
                )
                print(f"   (gets consolidated to: {consolidated_product.name})")
                conversion.delete()
                removed_count += 1

    print(f"\n✅ Removed {removed_count} wrong conversions")

    # Now let's test our fix by running the unit conversion loading
    print("\n=== Testing Fixed Unit Conversion Loading ===")
    from data_engineering.utils.unit_conversion import unit_conversion_service

    result = unit_conversion_service.load_legacy_unit_conversions_and_standards()
    print(f"Created {result['conversions_created']} new conversions")


if __name__ == "__main__":
    cleanup_wrong_conversions()

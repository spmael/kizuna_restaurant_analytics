#!/usr/bin/env python3
"""
Script to add missing unit conversion rules for products with high unit costs
"""

import os
import sys
from decimal import Decimal

import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.restaurant_data.models import Product, UnitConversion, UnitOfMeasure


def fix_missing_unit_conversions():
    print("=== Fixing Missing Unit Conversions ===\n")

    # Define the missing unit conversions based on typical package sizes
    missing_conversions = {
        # Spices and seasonings (typical package sizes)
        "pèbè": 50,  # 1 package = 50g
        "clou de girofle": 100,  # 1 package = 100g
        "coriandres": 25,  # 1 bunch = 25g (already exists but might be wrong name)
        "coriandre": 25,  # 1 bunch = 25g
        # Breadcrumbs and flour
        "fine chapelure": 500,  # 1 bag = 500g
        "fine chapelure pai": 500,  # 1 bag = 500g
        # Cheese
        "mozzarella": 250,  # 1 package = 250g
        # Seasoning cubes and powders
        "arômes maggi": 300,  # 1 cube = 300g (as per product name)
        "arômes maggi 300g": 300,  # 1 cube = 300g
        # Seeds
        "graine sesame": 200,  # 1 package = 200g
        "graine sésame": 200,  # 1 package = 200g
        # Vegetables (if purchased by unit)
        "céleris": 300,  # 1 bunch = 300g
        "céleri": 300,  # 1 bunch = 300g
    }

    # Get unit measures
    unit_measure = UnitOfMeasure.objects.filter(name="unit").first()
    g_measure = UnitOfMeasure.objects.filter(name="g").first()

    if not unit_measure or not g_measure:
        print("❌ Unit measures not found!")
        return

    print(f"✅ Using unit measures: {unit_measure.name} -> {g_measure.name}")

    conversions_created = 0
    conversions_updated = 0
    errors = 0

    for product_name_pattern, grams in missing_conversions.items():
        try:
            # Find products that match the pattern
            products = Product.objects.filter(name__icontains=product_name_pattern)

            for product in products:
                print(f"\n🔍 Checking: {product.name}")

                # Check if conversion already exists
                existing = UnitConversion.objects.filter(
                    from_unit=unit_measure, to_unit=g_measure, product=product
                ).first()

                if existing:
                    if existing.conversion_factor != Decimal(str(grams)):
                        print(
                            f"   ⚠️  Updating existing conversion: {existing.conversion_factor} -> {grams}"
                        )
                        existing.conversion_factor = Decimal(str(grams))
                        existing.notes = (
                            f"Product-specific conversion: 1 {product.name} = {grams}g"
                        )
                        existing.save()
                        conversions_updated += 1
                    else:
                        print(
                            f"   ✅ Conversion already correct: {existing.conversion_factor}"
                        )
                else:
                    # Create new conversion
                    UnitConversion.objects.create(
                        from_unit=unit_measure,
                        to_unit=g_measure,
                        conversion_factor=Decimal(str(grams)),
                        product=product,
                        is_active=True,
                        priority=10,
                        notes=f"Product-specific conversion: 1 {product.name} = {grams}g",
                    )
                    print(
                        f"   ➕ Created new conversion: {product.name} unit -> {grams}g"
                    )
                    conversions_created += 1

        except Exception as e:
            print(f"   ❌ Error processing {product_name_pattern}: {str(e)}")
            errors += 1

    print("\n=== Summary ===")
    print(f"✅ New conversions created: {conversions_created}")
    print(f"🔄 Existing conversions updated: {conversions_updated}")
    print(f"❌ Errors: {errors}")

    # Now let's check if we need to update existing ProductCostHistory records
    print("\n=== Checking ProductCostHistory Records ===")

    # Find products that might have wrong conversions
    products_to_fix = [
        "Pèbè",
        "Clou de girofle",
        "Fine chapelure pai",
        "Mozzarella",
        "arômes Maggi 300g",
        "GRAINE SESAME",
        "Céleris",
    ]

    from apps.analytics.models import ProductCostHistory

    for product_name in products_to_fix:
        product = Product.objects.filter(name__icontains=product_name).first()
        if product:
            # Check for records with conversion factor = 1.0 and unit cost > 100
            wrong_records = ProductCostHistory.objects.filter(
                product=product,
                recipe_conversion_factor=Decimal("1.000000"),
                unit_cost_in_recipe_units__gt=100,
            )

            if wrong_records.count() > 0:
                print(
                    f"\n⚠️  {product.name}: {wrong_records.count()} records with wrong conversion factor"
                )
                print(
                    "   These records need to be recalculated after unit conversion rules are added"
                )


if __name__ == "__main__":
    fix_missing_unit_conversions()

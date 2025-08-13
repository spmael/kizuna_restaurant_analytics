#!/usr/bin/env python3
"""
Script to update Paprika conversion factor to 150g
"""

import os
import sys
from decimal import Decimal

import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.analytics.models import ProductCostHistory
from apps.restaurant_data.models import Product, UnitConversion, UnitOfMeasure


def fix_paprika_conversion():
    print("=== Fixing Paprika Conversion Factor ===\n")

    unit_measure = UnitOfMeasure.objects.filter(name="unit").first()
    g_measure = UnitOfMeasure.objects.filter(name="g").first()

    if not unit_measure or not g_measure:
        print("❌ Unit measures not found!")
        return

    # Find Paprika product
    paprika = Product.objects.filter(name="Paprika").first()
    if not paprika:
        print("❌ Paprika product not found!")
        return

    print(f"✅ Found: {paprika.name}")

    # Check current conversion
    existing = UnitConversion.objects.filter(
        from_unit=unit_measure, to_unit=g_measure, product=paprika
    ).first()

    if existing:
        print(f"   - Current conversion: {existing.conversion_factor}")

        # Update to 150
        if existing.conversion_factor != Decimal("150.0"):
            print(f"   🔄 Updating conversion: {existing.conversion_factor} -> 150.0")
            existing.conversion_factor = Decimal("150.0")
            existing.notes = (
                f"Updated conversion: 1 {paprika.name} = 150g (market analysis)"
            )
            existing.save()
        else:
            print("   ✅ Conversion already correct: 150.0")
    else:
        # Create new conversion
        UnitConversion.objects.create(
            from_unit=unit_measure,
            to_unit=g_measure,
            conversion_factor=Decimal("150.0"),
            product=paprika,
            is_active=True,
            priority=10,
            notes=f"Product-specific conversion: 1 {paprika.name} = 150g (market analysis)",
        )
        print("   ➕ Created conversion: 1 unit -> 150g")

    # Recalculate existing ProductCostHistory records
    print("   🔄 Recalculating cost history records...")

    records_to_fix = ProductCostHistory.objects.filter(
        product=paprika, unit_cost_in_recipe_units__gt=0  # All records for this product
    )

    print(f"   Found {records_to_fix.count()} records to recalculate")

    for record in records_to_fix:
        try:
            # Get the updated conversion factor
            conversion = UnitConversion.objects.filter(
                from_unit=unit_measure,
                to_unit=g_measure,
                product=paprika,
                is_active=True,
            ).first()

            if conversion:
                # Recalculate
                new_recipe_quantity = (
                    record.quantity_ordered * conversion.conversion_factor
                )
                record.recipe_quantity = new_recipe_quantity
                record.recipe_conversion_factor = conversion.conversion_factor

                if new_recipe_quantity > 0:
                    new_unit_cost = record.total_amount / new_recipe_quantity
                    record.unit_cost_in_recipe_units = new_unit_cost
                else:
                    record.unit_cost_in_recipe_units = Decimal("0")

                record.cost_per_unit = record.unit_cost_in_recipe_units
                record.save()

                print(
                    f"     ✅ Updated record {record.id}: {record.quantity_ordered} unit -> {new_recipe_quantity} g = {new_unit_cost} FCFA/g"
                )
            else:
                print(f"     ❌ No conversion rule found for {paprika.name}")

        except Exception as e:
            print(f"     ❌ Error updating record {record.id}: {str(e)}")

    print("   ✅ Paprika conversion factor updated to 150g")


if __name__ == "__main__":
    fix_paprika_conversion()

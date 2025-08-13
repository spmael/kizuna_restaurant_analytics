#!/usr/bin/env python3
"""
Comprehensive validation script to check system integrity after fresh reload
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
from apps.restaurant_data.models import (
    Product,
    ProductConsolidation,
    UnitConversion,
    UnitOfMeasure,
)
from data_engineering.utils.product_consolidation import ProductConsolidationService
from data_engineering.utils.product_type_assignment import ProductTypeAssignmentService


def validate_reload():
    print("=== System Validation After Fresh Reload ===\n")

    # Initialize services
    consolidation_service = ProductConsolidationService()
    type_service = ProductTypeAssignmentService()

    # 1. Check basic data integrity
    print("1. Basic Data Integrity")
    print("-" * 30)

    product_count = Product.objects.count()
    conversion_count = UnitConversion.objects.count()
    consolidation_count = ProductConsolidation.objects.count()
    cost_history_count = ProductCostHistory.objects.count()

    print(f"✅ Products: {product_count}")
    print(f"✅ Unit Conversions: {conversion_count}")
    print(f"✅ Consolidation Rules: {consolidation_count}")
    print(f"✅ Cost History Records: {cost_history_count}")

    if product_count == 0:
        print("❌ No products found - data may not be loaded")
        return False

    print()

    # 2. Check consolidation rules
    print("2. Consolidation Rules")
    print("-" * 30)

    # Test key consolidation rules
    test_consolidations = [
        ("Ailes de Poulet au paprika", "Ailes de Poulet Cru (Kg)"),
        ("Mayonnaise ARMANTI", "Sauce Mayo"),
        ("Huile de tournesol", "Huile de Palme"),
    ]

    consolidation_issues = 0
    for original, expected_primary in test_consolidations:
        consolidated = consolidation_service.find_consolidated_product(original)
        if consolidated and consolidated.name == expected_primary:
            print(f"✅ {original} → {consolidated.name}")
        else:
            print(
                f"❌ {original} → {consolidated.name if consolidated else 'None'} (expected: {expected_primary})"
            )
            consolidation_issues += 1

    if consolidation_issues == 0:
        print("✅ All consolidation rules working correctly")
    else:
        print(f"❌ {consolidation_issues} consolidation issues found")

    print()

    # 3. Check unit conversions
    print("3. Unit Conversions")
    print("-" * 30)

    # Check key products that should have conversions
    key_products = [
        ("Paprika", 150),  # Should have 150g conversion
        ("Pommes de terre", 150),  # Should have 150g conversion
        ("Oignons", 120),  # Should have 120g conversion
    ]

    conversion_issues = 0
    unit_measure = UnitOfMeasure.objects.filter(name="unit").first()
    g_measure = UnitOfMeasure.objects.filter(name="g").first()

    if unit_measure and g_measure:
        for product_name, expected_grams in key_products:
            product = Product.objects.filter(name__iexact=product_name).first()
            if product:
                conversion = UnitConversion.objects.filter(
                    from_unit=unit_measure, to_unit=g_measure, product=product
                ).first()

                if conversion:
                    if conversion.conversion_factor == Decimal(str(expected_grams)):
                        print(f"✅ {product_name}: {conversion.conversion_factor}g")
                    else:
                        print(
                            f"⚠️  {product_name}: {conversion.conversion_factor}g (expected: {expected_grams}g)"
                        )
                        conversion_issues += 1
                else:
                    print(f"❌ {product_name}: No conversion found")
                    conversion_issues += 1
            else:
                print(f"❌ {product_name}: Product not found")
                conversion_issues += 1
    else:
        print("❌ Unit measures not found")
        conversion_issues += 1

    if conversion_issues == 0:
        print("✅ All key unit conversions present and correct")
    else:
        print(f"❌ {conversion_issues} conversion issues found")

    print()

    # 4. Check that consolidated products don't have wrong conversions
    print("4. Consolidated Product Conversions")
    print("-" * 30)

    consolidated_products_with_conversions = 0
    unit_conversions = (
        UnitConversion.objects.filter(from_unit=unit_measure, to_unit=g_measure)
        if unit_measure and g_measure
        else []
    )

    for conversion in unit_conversions:
        if conversion.product:
            consolidated = consolidation_service.find_consolidated_product(
                conversion.product.name
            )
            if consolidated and consolidated.id != conversion.product.id:
                print(
                    f"❌ {conversion.product.name} has conversion but gets consolidated to {consolidated.name}"
                )
                consolidated_products_with_conversions += 1

    if consolidated_products_with_conversions == 0:
        print("✅ No consolidated products have wrong conversions")
    else:
        print(
            f"❌ {consolidated_products_with_conversions} consolidated products have wrong conversions"
        )

    print()

    # 5. Check product type classification
    print("5. Product Type Classification")
    print("-" * 30)

    # Check that products are properly classified
    not_sold_count = 0
    resale_count = 0
    dish_count = 0

    for product in Product.objects.all()[:20]:  # Check first 20 products
        product_type = type_service.get_or_create_product_type(product)
        if product_type:
            if product_type.product_type == "not_sold":
                not_sold_count += 1
            elif product_type.product_type == "resale":
                resale_count += 1
            elif product_type.product_type == "dish":
                dish_count += 1

    print(
        f"✅ Product types: {resale_count} resale, {dish_count} dish, {not_sold_count} not_sold"
    )

    # Check for products that should be classified as resale but aren't
    resale_products = ["Paprika", "Pommes de terre", "Oignons"]
    classification_issues = 0

    for product_name in resale_products:
        product = Product.objects.filter(name__iexact=product_name).first()
        if product:
            product_type = type_service.get_or_create_product_type(product)
            if product_type and product_type.product_type != "resale":
                print(
                    f"⚠️  {product_name}: classified as {product_type.product_type} (expected: resale)"
                )
                classification_issues += 1

    if classification_issues == 0:
        print("✅ Product type classification looks correct")
    else:
        print(f"❌ {classification_issues} classification issues found")

    print()

    # 6. Check ProductCostHistory records
    print("6. Product Cost History")
    print("-" * 30)

    if cost_history_count > 0:
        # Check for records with conversion factor = 1.0 (potential issues)
        wrong_conversions = ProductCostHistory.objects.filter(
            recipe_conversion_factor=Decimal("1.000000"),
            unit_cost_in_recipe_units__gt=100,  # High unit cost suggests wrong conversion
        ).count()

        if wrong_conversions > 0:
            print(
                f"⚠️  {wrong_conversions} cost history records with potential wrong conversions"
            )
        else:
            print("✅ No obvious wrong conversions in cost history")

        # Check sample records
        sample_records = ProductCostHistory.objects.all()[:5]
        for record in sample_records:
            print(
                f"  - {record.product.name}: {record.recipe_conversion_factor} factor, {record.unit_cost_in_recipe_units} cost"
            )
    else:
        print("⚠️  No cost history records found")

    print()

    # 7. Overall system health
    print("7. Overall System Health")
    print("-" * 30)

    total_issues = (
        consolidation_issues
        + conversion_issues
        + consolidated_products_with_conversions
        + classification_issues
    )

    if total_issues == 0:
        print("🎉 SYSTEM VALIDATION PASSED - All systems working correctly!")
        return True
    else:
        print(f"❌ SYSTEM VALIDATION FAILED - {total_issues} issues found")
        print("\nRecommendations:")
        if consolidation_issues > 0:
            print("- Check consolidation rule loading")
        if conversion_issues > 0:
            print("- Check unit conversion loading")
        if consolidated_products_with_conversions > 0:
            print("- Run cleanup script to remove wrong conversions")
        if classification_issues > 0:
            print("- Check product type classification logic")
        return False


def quick_fix_suggestions():
    """Provide quick fix suggestions for common issues"""
    print("\n=== Quick Fix Suggestions ===")

    print("\n1. If consolidation rules are missing:")
    print(
        '   python manage.py shell -c "from data_engineering.utils.product_consolidation import ProductConsolidationService; ProductConsolidationService().load_legacy_consolidation_rules()"'
    )

    print("\n2. If unit conversions are missing:")
    print(
        '   python manage.py shell -c "from data_engineering.utils.unit_conversion import unit_conversion_service; unit_conversion_service.load_legacy_unit_conversions_and_standards()"'
    )

    print("\n3. If product types are wrong:")
    print("   python manage.py fix_product_classifications")

    print("\n4. If cost history has wrong conversions:")
    print("   python manage.py regenerate_cost_history")

    print("\n5. If consolidated products have wrong conversions:")
    print("   python cleanup_wrong_conversions.py")


if __name__ == "__main__":
    success = validate_reload()
    if not success:
        quick_fix_suggestions()

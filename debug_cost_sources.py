#!/usr/bin/env python
"""
Debug script to check cost sources for ingredients
"""

import os
from datetime import date

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.analytics.models import ProductCostHistory
from apps.analytics.services.ingredient_costing import ProductCostingService
from apps.restaurant_data.models import Product


def debug_cost_sources():
    """Debug what cost sources are being used"""

    print("=== DEBUGGING COST SOURCES ===\n")

    # Check Huile de Palme specifically
    huile = Product.objects.filter(name__icontains="Huile de Palme").first()
    if not huile:
        print("Huile de Palme not found!")
        return

    print(f"Product: {huile.name}")
    print(f"Current cost per unit (Product table): {huile.current_cost_per_unit} FCFA")
    print(f"Unit of measure: {huile.unit_of_measure.name}")
    print()

    # Check ProductCostHistory
    history = ProductCostHistory.objects.filter(product=huile).order_by(
        "-purchase_date"
    )[:5]
    print(f"ProductCostHistory records: {history.count()}")
    for h in history:
        print(
            f"  {h.purchase_date}: {h.unit_cost_in_recipe_units} FCFA per {h.recipe_quantity} {huile.unit_of_measure.name}"
        )
    print()

    # Test the get_current_product_cost method
    target_date = date(2025, 4, 5)
    product_costing_service = ProductCostingService()

    # Clear the cache first
    product_costing_service.cost_cache = {}

    print(f"Testing get_current_product_cost for {target_date} (cache cleared):")
    current_cost = product_costing_service.get_current_product_cost(huile, target_date)
    print(f"  Result: {current_cost} FCFA")
    print()

    # Check what the fallback method returns
    print("Testing _get_fallback_cost:")
    fallback_cost = product_costing_service._get_fallback_cost(huile)
    print(f"  Result: {fallback_cost} FCFA")
    print()

    # Check if there are any recent purchases in the lookback period
    from datetime import timedelta

    from django.utils import timezone

    lookback_date = timezone.now() - timedelta(days=90)
    recent_history = ProductCostHistory.objects.filter(
        product=huile, purchase_date__gte=lookback_date, is_active=True
    )

    print(f"Recent purchases (last 90 days): {recent_history.count()}")
    for h in recent_history:
        print(f"  {h.purchase_date}: {h.unit_cost_in_recipe_units} FCFA")

    print("\n" + "=" * 60 + "\n")

    # Check a few other expensive ingredients
    expensive_ingredients = ["SEL FIN", "arômes Maggi 300g", "Feuilles de Basilic"]

    for ingredient_name in expensive_ingredients:
        product = Product.objects.filter(name__icontains=ingredient_name).first()
        if product:
            print(f"Ingredient: {product.name}")
            print(
                f"  Product.current_cost_per_unit: {product.current_cost_per_unit} FCFA"
            )

            # Check ProductCostHistory
            history_count = ProductCostHistory.objects.filter(product=product).count()
            print(f"  ProductCostHistory records: {history_count}")

            if history_count > 0:
                latest_history = (
                    ProductCostHistory.objects.filter(product=product)
                    .order_by("-purchase_date")
                    .first()
                )
                print(
                    f"  Latest history: {latest_history.unit_cost_in_recipe_units} FCFA"
                )

            # Test get_current_product_cost with cleared cache
            product_costing_service.cost_cache = {}
            current_cost = product_costing_service.get_current_product_cost(
                product, target_date
            )
            print(f"  get_current_product_cost result: {current_cost} FCFA")
            print()


if __name__ == "__main__":
    debug_cost_sources()

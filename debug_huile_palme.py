#!/usr/bin/env python
"""
Debug script to investigate Huile de Palme cost calculation
"""

import os
import django
from datetime import date, timedelta
from decimal import Decimal

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.analytics.models import ProductCostHistory
from apps.analytics.services.ingredient_costing import ProductCostingService
from apps.restaurant_data.models import Product

def debug_huile_palme():
    """Debug the Huile de Palme cost calculation"""
    
    print("=== DEBUGGING HUILE DE PALME COST CALCULATION ===\n")
    
    # Find Huile de Palme
    huile = Product.objects.filter(name__icontains='Huile de Palme').first()
    if not huile:
        print("Huile de Palme not found!")
        return
    
    print(f"Product: {huile.name}")
    print(f"Unit of measure: {huile.unit_of_measure.name}")
    print()
    
    # Check all ProductCostHistory records
    all_history = ProductCostHistory.objects.filter(product=huile).order_by('-purchase_date')
    print(f"Total ProductCostHistory records: {all_history.count()}")
    print("All history records:")
    for h in all_history:
        print(f"  {h.purchase_date}: {h.unit_cost_in_recipe_units} FCFA per {h.recipe_quantity} {huile.unit_of_measure.name}")
    print()
    
    # Test for April 5, 2025 specifically
    target_date = date(2025, 4, 5)
    print(f"Testing for target date: {target_date}")
    
    # Check what purchases are available for the lookback period
    lookback_date = target_date - timedelta(days=90)
    print(f"Lookback period: {lookback_date} to {target_date}")
    
    recent_history = ProductCostHistory.objects.filter(
        product=huile,
        purchase_date__gte=lookback_date,
        purchase_date__lte=target_date,
        is_active=True
    ).order_by('-purchase_date')
    
    print(f"Recent purchases in lookback period: {recent_history.count()}")
    for h in recent_history:
        print(f"  {h.purchase_date}: {h.unit_cost_in_recipe_units} FCFA")
    print()
    
    # Test the ProductCostingService
    product_costing_service = ProductCostingService()
    product_costing_service.cost_cache = {}  # Clear cache
    
    print("Testing ProductCostingService methods:")
    
    # Test get_current_product_cost
    current_cost = product_costing_service.get_current_product_cost(huile, target_date)
    print(f"  get_current_product_cost: {current_cost} FCFA")
    
    # Test _get_fallback_cost
    fallback_cost = product_costing_service._get_fallback_cost(huile)
    print(f"  _get_fallback_cost: {fallback_cost} FCFA")
    
    # Test _calculate_weighted_average_cost directly
    weighted_cost = product_costing_service._calculate_weighted_average_cost(huile, target_date)
    print(f"  _calculate_weighted_average_cost: {weighted_cost} FCFA")
    
    print()
    
    # Check if there are any purchases before the target date
    purchases_before = ProductCostHistory.objects.filter(
        product=huile,
        purchase_date__lte=target_date,
        is_active=True
    ).order_by('-purchase_date')
    
    print(f"Purchases before or on {target_date}: {purchases_before.count()}")
    for h in purchases_before[:5]:  # Show first 5
        print(f"  {h.purchase_date}: {h.unit_cost_in_recipe_units} FCFA")
    
    if purchases_before.count() > 5:
        print(f"  ... and {purchases_before.count() - 5} more")

if __name__ == "__main__":
    debug_huile_palme()

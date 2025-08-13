#!/usr/bin/env python
"""
Script to fix the Huile de Palme record from April 4, 2025
"""

import os
import django
from datetime import date
from decimal import Decimal

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.analytics.models import ProductCostHistory
from apps.restaurant_data.models import Product, UnitOfMeasure

def fix_huile_record():
    """Fix the Huile de Palme record from April 4, 2025"""
    
    print("=== FIXING HUILE DE PALME RECORD FROM APRIL 4, 2025 ===\n")
    
    # Find the product and unit
    huile = Product.objects.filter(name__icontains='Huile de Palme').first()
    l_unit = UnitOfMeasure.objects.filter(name='l').first()
    
    if not huile:
        print("Huile de Palme product not found!")
        return
    
    if not l_unit:
        print("Liter unit not found!")
        return
    
    # Find the problematic record
    wrong_record = ProductCostHistory.objects.filter(
        product=huile, 
        purchase_date__year=2025, 
        purchase_date__month=4, 
        purchase_date__day=4
    ).first()
    
    if not wrong_record:
        print("No record found for April 4, 2025!")
        return
    
    print(f"Found record: {wrong_record.purchase_date}")
    print(f"Old values:")
    print(f"  Unit cost: {wrong_record.unit_cost_in_recipe_units} FCFA")
    print(f"  Recipe quantity: {wrong_record.recipe_quantity}")
    print(f"  Unit of recipe: {wrong_record.unit_of_recipe.name}")
    
    # Fix the record
    # Convert 12 ml to 0.012 l
    wrong_record.recipe_quantity = Decimal('0.012')
    wrong_record.unit_of_recipe = l_unit
    wrong_record.unit_cost_in_recipe_units = Decimal('18000.00') / Decimal('0.012')
    wrong_record.save()
    
    print(f"\nNew values:")
    print(f"  Unit cost: {wrong_record.unit_cost_in_recipe_units} FCFA")
    print(f"  Recipe quantity: {wrong_record.recipe_quantity}")
    print(f"  Unit of recipe: {wrong_record.unit_of_recipe.name}")
    print("\nRecord fixed successfully!")

if __name__ == "__main__":
    fix_huile_record()

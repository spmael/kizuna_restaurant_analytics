#!/usr/bin/env python
"""
Debug script to step through recipe costing for Poulet Braisé (Quartier)
"""

import os
from datetime import date
from decimal import Decimal

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.analytics.services.ingredient_costing import ProductCostingService
from apps.analytics.services.recipe_costing import RecipeCostingService
from apps.recipes.models import Recipe
from apps.restaurant_data.models import Sales


def debug_recipe_costing():
    """Debug the recipe costing for Poulet Braisé (Quartier)"""

    print("=== DEBUGGING RECIPE COSTING FOR POULET BRAISÉ (QUARTIER) ===\n")

    # 1. Find the sales for Poulet Braisé (Quartier) on April 5, 2025
    target_date = date(2025, 4, 5)
    poulet_sales = Sales.objects.filter(
        sale_date=target_date, product__name__icontains="Poulet Braisé"
    )

    print(f"Found {poulet_sales.count()} Poulet Braisé sales on {target_date}")
    for sale in poulet_sales:
        print(
            f"  - {sale.product.name}: {sale.quantity_sold} units at {sale.unit_sale_price} FCFA each"
        )

    print("\n" + "=" * 60 + "\n")

    # 2. Find the recipe being used
    poulet_product = poulet_sales.first().product if poulet_sales.exists() else None
    if poulet_product:
        print(f"Product: {poulet_product.name}")

        # Try to find matching recipe
        recipe = Recipe.objects.filter(
            dish_name__icontains=poulet_product.name, is_active=True
        ).first()

        if recipe:
            print(f"Recipe found: {recipe.dish_name}")
            print(f"Serving size: {recipe.serving_size}")
            print(f"Number of ingredients: {recipe.ingredients.count()}")
        else:
            print("No recipe found!")
            return

    print("\n" + "=" * 60 + "\n")

    # 3. Calculate recipe cost step by step
    recipe_costing_service = RecipeCostingService()
    product_costing_service = ProductCostingService()

    print("=== INGREDIENT COST BREAKDOWN ===\n")

    total_ingredient_cost = Decimal("0")

    for i, recipe_ingredient in enumerate(recipe.ingredients.all()):
        ingredient = recipe_ingredient.ingredient
        quantity = recipe_ingredient.quantity
        unit = recipe_ingredient.unit_of_recipe

        # Get current cost for this ingredient
        current_cost = product_costing_service.get_current_product_cost(
            ingredient, target_date
        )

        # Calculate cost for this ingredient
        ingredient_total_cost = current_cost * quantity
        ingredient_cost_per_portion = (
            ingredient_total_cost / recipe.serving_size
            if recipe.serving_size > 0
            else Decimal("0")
        )

        total_ingredient_cost += ingredient_total_cost

        print(f"Ingredient {i+1}: {ingredient.name}")
        print(f"  Quantity: {quantity} {unit}")
        print(f"  Current cost per unit: {current_cost} FCFA")
        print(f"  Total cost for recipe: {ingredient_total_cost} FCFA")
        print(f"  Cost per portion: {ingredient_cost_per_portion} FCFA")
        print()

    print(f"TOTAL INGREDIENT COST: {total_ingredient_cost} FCFA")
    print(
        f"COST PER PORTION: {total_ingredient_cost / recipe.serving_size if recipe.serving_size > 0 else 0} FCFA"
    )

    print("\n" + "=" * 60 + "\n")

    # 4. Calculate full recipe cost with waste and labor
    print("=== FULL RECIPE COST CALCULATION ===\n")

    # Calculate waste cost
    waste_cost = total_ingredient_cost * (recipe.waste_factor_percentage / 100)
    print(f"Waste factor: {recipe.waste_factor_percentage}%")
    print(f"Waste cost: {waste_cost} FCFA")

    # Calculate labor cost
    labor_cost = (
        total_ingredient_cost * (recipe.labour_cost_percentage / 100)
    ) * recipe.serving_size
    print(f"Labor factor: {recipe.labour_cost_percentage}%")
    print(f"Labor cost: {labor_cost} FCFA")

    # Total recipe cost
    total_recipe_cost = total_ingredient_cost + waste_cost + labor_cost
    cost_per_portion = (
        total_recipe_cost / recipe.serving_size
        if recipe.serving_size > 0
        else Decimal("0")
    )

    print(f"\nTOTAL RECIPE COST: {total_recipe_cost} FCFA")
    print(f"COST PER PORTION: {cost_per_portion} FCFA")

    print("\n" + "=" * 60 + "\n")

    # 5. Calculate cost for actual sales
    print("=== SALES COST CALCULATION ===\n")

    for sale in poulet_sales:
        sale_cost = cost_per_portion * sale.quantity_sold
        print(f"Sale: {sale.product.name}")
        print(f"  Quantity sold: {sale.quantity_sold}")
        print(f"  Cost per portion: {cost_per_portion} FCFA")
        print(f"  Total cost for this sale: {sale_cost} FCFA")
        print(f"  Selling price: {sale.unit_sale_price} FCFA")
        print(f"  Revenue: {sale.total_sale_price} FCFA")
        print()

    print("=== SUMMARY ===")
    print(
        f"The issue is that '{recipe.dish_name}' (whole chicken recipe) is being used"
    )
    print(f"for '{poulet_product.name}' (quarter chicken) sales.")
    print(
        "This inflates the cost by using the full chicken recipe instead of 1/4 portions."
    )


if __name__ == "__main__":
    debug_recipe_costing()

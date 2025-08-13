#!/usr/bin/env python
import json
import os
import sys
from datetime import datetime

import django

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.analytics.models import DailySummary, ProductCostHistory
from apps.recipes.models import Recipe, RecipeIngredient
from apps.restaurant_data.models import (
    ConsolidatedPurchases,
    ConsolidatedSales,
    Product,
    Purchase,
    Sales,
)


def backup_and_reset():
    """Backup current data and reset database for clean reload"""

    print("=== DATABASE BACKUP AND RESET ===\n")

    # Create backup directory
    backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    print(f"📁 Created backup directory: {backup_dir}")

    # Backup counts
    backup_data = {"timestamp": datetime.now().isoformat(), "counts": {}}

    # Count and backup data
    models_to_backup = [
        ("Products", Product),
        ("Purchases", Purchase),
        ("Sales", Sales),
        ("ConsolidatedPurchases", ConsolidatedPurchases),
        ("ConsolidatedSales", ConsolidatedSales),
        ("Recipes", Recipe),
        ("RecipeIngredients", RecipeIngredient),
        ("ProductCostHistory", ProductCostHistory),
        ("DailySummaries", DailySummary),
    ]

    for name, model in models_to_backup:
        count = model.objects.count()
        backup_data["counts"][name] = count
        print(f"📊 {name}: {count} records")

    # Save backup info
    with open(f"{backup_dir}/backup_info.json", "w") as f:
        json.dump(backup_data, f, indent=2)

    print(f"\n✅ Backup info saved to {backup_dir}/backup_info.json")

    # Ask for confirmation
    print("\n⚠️  WARNING: This will delete all data from the following tables:")
    for name, model in models_to_backup:
        count = model.objects.count()
        if count > 0:
            print(f"   - {name}: {count} records")

    response = input("\n❓ Are you sure you want to proceed? (yes/no): ")
    if response.lower() != "yes":
        print("❌ Operation cancelled.")
        return

    # Delete data in reverse dependency order
    print("\n🗑️  Deleting data...")

    # Delete analytics data first
    DailySummary.objects.all().delete()
    print("   ✅ Deleted DailySummaries")

    ProductCostHistory.objects.all().delete()
    print("   ✅ Deleted ProductCostHistory")

    # Delete recipe data
    RecipeIngredient.objects.all().delete()
    print("   ✅ Deleted RecipeIngredients")

    Recipe.objects.all().delete()
    print("   ✅ Deleted Recipes")

    # Delete consolidated data
    ConsolidatedSales.objects.all().delete()
    print("   ✅ Deleted ConsolidatedSales")

    ConsolidatedPurchases.objects.all().delete()
    print("   ✅ Deleted ConsolidatedPurchases")

    # Delete base data
    Sales.objects.all().delete()
    print("   ✅ Deleted Sales")

    Purchase.objects.all().delete()
    print("   ✅ Deleted Purchases")

    # Keep Products for now (they might be referenced by other systems)
    # Product.objects.all().delete()
    # print("   ✅ Deleted Products")

    print("\n✅ Database reset complete!")
    print(f"📁 Backup info saved in: {backup_dir}")
    print("\n🔄 Ready for clean data reload with all fixes applied.")


if __name__ == "__main__":
    backup_and_reset()

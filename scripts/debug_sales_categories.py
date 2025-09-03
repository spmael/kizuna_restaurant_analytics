#!/usr/bin/env python
"""
Debug script to investigate sales by category issues.
Run with: python manage.py shell < scripts/debug_sales_categories.py
"""

import os
import sys

import django

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    print(
        "Please run this script with: python manage.py shell < scripts/debug_sales_categories.py"
    )
    sys.exit(1)

from datetime import timedelta

from django.db.models import Avg, Count, Sum

from apps.analytics.models import DailySummary
from apps.restaurant_data.models import Product, Sales, SalesCategory


def debug_sales_categories():
    """Debug the sales by category functionality"""

    print("=== SALES BY CATEGORY DEBUG ===\n")

    # 1. Check if we have any sales data
    total_sales = Sales.objects.count()
    print(f"1. Total sales records: {total_sales}")

    if total_sales == 0:
        print("   ❌ No sales data found!")
        return

    # 2. Check sales categories
    sales_categories = SalesCategory.objects.filter(is_active=True)
    print(f"2. Active sales categories: {sales_categories.count()}")

    for cat in sales_categories:
        print(f"   - {cat.name} (ID: {cat.id})")

    # 3. Check products and their categories
    products_with_sales = Product.objects.filter(sales__isnull=False).distinct()
    print(f"\n3. Products with sales: {products_with_sales.count()}")

    products_without_category = products_with_sales.filter(
        sales_category__isnull=True
    ).count()
    print(f"   Products without sales category: {products_without_category}")

    if products_without_category > 0:
        print("   ❌ Found products without sales categories!")
        sample_products = products_with_sales.filter(sales_category__isnull=True)[:5]
        for prod in sample_products:
            print(f"      - {prod.name} (ID: {prod.id})")

    # 4. Check the actual query that's failing
    print("\n4. Testing the actual query from revenue analytics:")

    # Get a date range (last 30 days or available data)
    latest_sale = Sales.objects.order_by("-sale_date").first()
    if latest_sale:
        end_date = latest_sale.sale_date
        start_date = end_date - timedelta(days=30)

        print(f"   Date range: {start_date} to {end_date}")

        # Test the exact query from revenue analytics
        category_sales = (
            Sales.objects.filter(sale_date__range=[start_date, end_date])
            .values("product__sales_category__name")
            .annotate(
                total_revenue=Sum("total_sale_price"),
                total_quantity=Sum("quantity_sold"),
                order_count=Count("order_number", distinct=True),
                avg_unit_price=Avg("unit_sale_price"),
            )
            .order_by("-total_revenue")
        )

        print(f"   Categories found: {category_sales.count()}")

        for item in category_sales:
            category_name = item["product__sales_category__name"] or "NULL"
            revenue = item["total_revenue"]
            print(f"      - {category_name}: {revenue} FCFA")

    # 5. Check for orphaned sales (sales without valid products)
    orphaned_sales = Sales.objects.filter(product__isnull=True).count()
    print(f"\n5. Orphaned sales (no product): {orphaned_sales}")

    # 6. Check for sales with products but no categories
    sales_no_category = Sales.objects.filter(
        product__sales_category__isnull=True
    ).count()
    print(f"6. Sales with products but no category: {sales_no_category}")

    if sales_no_category > 0:
        print("   ❌ Found sales without categories!")
        sample_sales = Sales.objects.filter(
            product__sales_category__isnull=True
        ).select_related("product")[:5]

        for sale in sample_sales:
            print(
                f"      - Sale {sale.id}: {sale.product.name if sale.product else 'No Product'} (Date: {sale.sale_date})"
            )

    # 7. Check daily summaries for category data
    print("\n7. Daily summaries with category data:")
    latest_summary = DailySummary.objects.order_by("-date").first()
    if latest_summary:
        print(f"   Latest summary date: {latest_summary.date}")
        print(f"   Total sales: {latest_summary.total_sales}")
        print(f"   Total orders: {latest_summary.total_orders}")

    print("\n=== END DEBUG ===\n")


if __name__ == "__main__":
    debug_sales_categories()

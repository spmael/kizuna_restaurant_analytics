#!/usr/bin/env python
"""
Test script for the African-inspired Restaurant Analytics Dashboard
"""

import os
import sys
from datetime import date, timedelta
from decimal import Decimal

import django

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.db.models import Avg, Sum

from apps.analytics.models import DailySummary
from apps.analytics.services.services import DailyAnalyticsService
from apps.restaurant_data.models import (
    Product,
    PurchasesCategory,
    SalesCategory,
    UnitOfMeasure,
)


def create_sample_data():
    """Create sample data for testing the dashboard"""

    # Create sample categories and units if they don't exist
    main_dishes_category, _ = PurchasesCategory.objects.get_or_create(
        name="Main Dishes",
        defaults={"name_fr": "Plats Principaux", "name_en": "Main Dishes"},
    )

    side_dishes_category, _ = PurchasesCategory.objects.get_or_create(
        name="Side Dishes",
        defaults={"name_fr": "Accompagnements", "name_en": "Side Dishes"},
    )

    # Create sales categories
    food_sales_category, _ = SalesCategory.objects.get_or_create(
        name="Food", defaults={"name_fr": "Nourriture", "name_en": "Food"}
    )

    # Create units of measure
    pieces_unit, _ = UnitOfMeasure.objects.get_or_create(
        name="Pieces",
        defaults={"abbreviation": "pcs", "name_fr": "Pièces", "name_en": "Pieces"},
    )

    kg_unit, _ = UnitOfMeasure.objects.get_or_create(
        name="Kilogram",
        defaults={"abbreviation": "kg", "name_fr": "Kilogramme", "name_en": "Kilogram"},
    )

    # Create sample products if they don't exist
    products = []
    product_data = [
        {
            "name": "Grilled Chicken",
            "purchase_category": main_dishes_category,
            "sales_category": food_sales_category,
            "unit_of_measure": pieces_unit,
            "current_selling_price": Decimal("15.00"),
            "current_cost_per_unit": Decimal("8.00"),
            "current_stock": Decimal("50.00"),
        },
        {
            "name": "Beef Steak",
            "purchase_category": main_dishes_category,
            "sales_category": food_sales_category,
            "unit_of_measure": pieces_unit,
            "current_selling_price": Decimal("18.00"),
            "current_cost_per_unit": Decimal("10.00"),
            "current_stock": Decimal("30.00"),
        },
        {
            "name": "Fish Curry",
            "purchase_category": main_dishes_category,
            "sales_category": food_sales_category,
            "unit_of_measure": pieces_unit,
            "current_selling_price": Decimal("12.00"),
            "current_cost_per_unit": Decimal("6.00"),
            "current_stock": Decimal("40.00"),
        },
        {
            "name": "Vegetable Soup",
            "purchase_category": side_dishes_category,
            "sales_category": food_sales_category,
            "unit_of_measure": pieces_unit,
            "current_selling_price": Decimal("8.00"),
            "current_cost_per_unit": Decimal("4.00"),
            "current_stock": Decimal("60.00"),
        },
        {
            "name": "Rice",
            "purchase_category": side_dishes_category,
            "sales_category": food_sales_category,
            "unit_of_measure": kg_unit,
            "current_selling_price": Decimal("5.00"),
            "current_cost_per_unit": Decimal("2.50"),
            "current_stock": Decimal("100.00"),
        },
        {
            "name": "French Fries",
            "purchase_category": side_dishes_category,
            "sales_category": food_sales_category,
            "unit_of_measure": kg_unit,
            "current_selling_price": Decimal("6.00"),
            "current_cost_per_unit": Decimal("3.00"),
            "current_stock": Decimal("80.00"),
        },
    ]

    for product_info in product_data:
        product, created = Product.objects.get_or_create(
            name=product_info["name"], defaults=product_info
        )
        products.append(product)
        if created:
            print(f"Created product: {product_info['name']}")

    # Create sample daily summaries for the last 7 days
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=6)

    for i in range(7):
        current_date = start_date + timedelta(days=i)

        # Check if summary already exists
        if DailySummary.objects.filter(date=current_date).exists():
            print(f"Daily summary for {current_date} already exists, skipping...")
            continue

        # Create sample data with realistic restaurant metrics
        base_sales = 15000 + (i * 2000)  # Increasing trend
        base_orders = 50 + (i * 5)
        base_customers = 60 + (i * 8)

        summary = DailySummary.objects.create(
            date=current_date,
            total_sales=Decimal(str(base_sales)),
            total_orders=base_orders,
            total_customers=base_customers,
            average_order_value=Decimal(str(base_sales / base_orders)),
            average_ticket_size=Decimal(str(base_sales / base_customers)),
            # Payment methods
            cash_sales=Decimal(str(base_sales * 0.4)),
            mobile_money_sales=Decimal(str(base_sales * 0.3)),
            credit_card_sales=Decimal(str(base_sales * 0.2)),
            other_payment_methods_sales=Decimal(str(base_sales * 0.1)),
            # Cost metrics
            total_food_cost=Decimal(str(base_sales * 0.32)),  # 32% food cost
            resale_cost=Decimal(str(base_sales * 0.08)),  # 8% resale cost
            food_cost_percentage=Decimal("32.0"),
            # Profitability
            gross_profit=Decimal(str(base_sales * 0.60)),
            gross_profit_margin=Decimal("60.0"),
            # Operational metrics
            total_items_sold=base_orders * 2,  # Average 2 items per order
            average_items_per_order=Decimal("2.0"),
            dine_in_orders=int(base_orders * 0.6),
            take_out_orders=int(base_orders * 0.3),
            delivery_orders=int(base_orders * 0.1),
            # Time-based breakdown
            lunch_sales=Decimal(str(base_sales * 0.4)),
            dinner_sales=Decimal(str(base_sales * 0.6)),
            peak_hour_sales=Decimal(str(base_sales * 0.25)),
            # Quality metrics
            waste_cost=Decimal(str(base_sales * 0.02)),  # 2% waste
            comps_and_discounts=Decimal(str(base_sales * 0.01)),  # 1% comps
            # Staff metrics
            staff_count=8,
            sales_per_staff=Decimal(str(base_sales / 8)),
            # External factors
            weather_conditions="sunny",
            is_holiday=False,
            special_events="",
            # Notes
            manager_notes=f"Sample data for {current_date}",
        )

        print(f"Created daily summary for {current_date}: {summary.total_sales} FCFA")


def test_dashboard_data():
    """Test that the dashboard has the required data"""

    # Test recent summaries
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=6)

    recent_summaries = DailySummary.objects.filter(
        date__range=[start_date, end_date]
    ).order_by("date")

    print("\n📊 Dashboard Data Test Results:")
    print(f"Date range: {start_date} to {end_date}")
    print(f"Found {recent_summaries.count()} daily summaries")

    if recent_summaries.count() > 0:
        # Calculate week totals
        week_totals = recent_summaries.aggregate(
            total_sales=Sum("total_sales"),
            total_orders=Sum("total_orders"),
            avg_food_cost_pct=Avg("food_cost_percentage"),
        )

        print("📈 Week Totals:")
        print(f"  - Total Sales: {week_totals['total_sales']:,.0f} FCFA")
        print(f"  - Total Orders: {week_totals['total_orders']}")
        print(f"  - Avg Food Cost: {week_totals['avg_food_cost_pct']:.1f}%")

        # Test yesterday's data
        yesterday = DailySummary.objects.filter(date=end_date).first()
        if yesterday:
            print("\n📅 Yesterday's Performance:")
            print(f"  - Sales: {yesterday.total_sales:,.0f} FCFA")
            print(f"  - Orders: {yesterday.total_orders}")
            print(f"  - Customers: {yesterday.total_customers}")
            print(f"  - Avg Order Value: {yesterday.average_order_value:,.0f} FCFA")
            print(f"  - Food Cost: {yesterday.food_cost_percentage:.1f}%")

            # Test food cost status
            if yesterday.food_cost_percentage > 35:
                print(f"  ⚠️  Food cost is HIGH ({yesterday.food_cost_percentage:.1f}%)")
            elif yesterday.food_cost_percentage <= 30:
                print(
                    f"  ✅ Food cost is EXCELLENT ({yesterday.food_cost_percentage:.1f}%)"
                )
            else:
                print(
                    f"  ⚠️  Food cost is ACCEPTABLE ({yesterday.food_cost_percentage:.1f}%)"
                )

        # Test service methods
        service = DailyAnalyticsService()
        try:
            top_products = service.get_sales_by_product(end_date)[:3]
            print("\n🏆 Top Products (Yesterday):")
            for i, product in enumerate(top_products, 1):
                print(
                    f"  {i}. {product['product__name']}: {product['total_revenue']:,.0f} FCFA"
                )
        except Exception as e:
            print(f"⚠️  Could not fetch top products: {e}")

    else:
        print("❌ No daily summaries found for the test period")


def test_urls():
    """Test that the dashboard URLs are accessible"""

    print("\n🔗 URL Test Results:")

    # Test URLs (these would be tested in a real Django test)
    urls_to_test = [
        "/analytics/",
        "/analytics/african/",
        "/analytics/sales/",
        "/analytics/costs/",
        "/analytics/performance/",
    ]

    for url in urls_to_test:
        print(f"  - {url} (would test in Django test suite)")


def main():
    """Main test function"""

    print("🌍 African-Inspired Restaurant Analytics Dashboard Test")
    print("=" * 60)

    # Create sample data
    print("\n📝 Creating sample data...")
    create_sample_data()

    # Test dashboard data
    test_dashboard_data()

    # Test URLs
    test_urls()

    print("\n✅ Test completed!")
    print("\n🎨 To view the dashboards:")
    print("  - Classic Dashboard: http://localhost:8000/analytics/")
    print("  - African Design: http://localhost:8000/analytics/african/")
    print("\n📚 For documentation, see: AFRICAN_DASHBOARD_README.md")


if __name__ == "__main__":
    main()

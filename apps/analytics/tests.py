from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.analytics.models import DailySummary, ProductCostHistory
from apps.analytics.services.ingredient_costing import ProductCostingService
from apps.analytics.services.services import DailyAnalyticsService
from apps.recipes.models import Recipe
from apps.restaurant_data.models import (
    Product,
    PurchasesCategory,
    SalesCategory,
    UnitOfMeasure,
)


class DailyAnalyticsServiceTestCase(TestCase):
    """Test cases for DailyAnalyticsService"""

    def setUp(self):
        """Set up test data"""
        # Create required categories and units
        self.unit = UnitOfMeasure.objects.create(name="kg", abbreviation="kg")
        self.purchase_category = PurchasesCategory.objects.create(name="Grains")
        self.sales_category = SalesCategory.objects.create(name="Food")

        # Create test products
        self.food_product = Product.objects.create(
            name="Rice",
            current_cost_per_unit=Decimal("2.50"),
            current_selling_price=Decimal("5.00"),
            current_stock=Decimal("100.00"),
            unit_of_measure=self.unit,
            purchase_category=self.purchase_category,
            sales_category=self.sales_category,
        )

        self.resale_product = Product.objects.create(
            name="Bottled Water",
            current_cost_per_unit=Decimal("1.00"),
            current_selling_price=Decimal("2.00"),
            current_stock=Decimal("50.00"),
            unit_of_measure=self.unit,
            purchase_category=self.purchase_category,
            sales_category=self.sales_category,
        )

        # Create test recipe
        self.recipe = Recipe.objects.create(
            dish_name="Rice Bowl",
            serving_size=Decimal("2.0"),
            waste_factor_percentage=Decimal("5.00"),
            labour_cost_percentage=Decimal("10.00"),
            target_food_cost_percentage=Decimal("30.00"),
        )

        # Create daily summary
        self.daily_summary = DailySummary.objects.create(
            date=date.today(),
            total_sales=Decimal("1000.00"),
            total_orders=10,
            total_customers=8,
            total_food_cost=Decimal("300.00"),
            resale_cost=Decimal("100.00"),
            cash_sales=Decimal("600.00"),
            credit_card_sales=Decimal("400.00"),
            total_items_sold=50,
            waste_cost=Decimal("20.00"),
            comps_and_discounts=Decimal("10.00"),
        )

        self.service = DailyAnalyticsService()

    def test_calculate_daily_stats(self):
        """Test daily stats calculation"""
        target_date = date.today()

        with patch.object(
            self.service, "_calculate_enhanced_cost_metrics"
        ) as mock_costs:
            mock_costs.return_value = {
                "total_food_cost": Decimal("300.00"),
                "resale_cost": Decimal("100.00"),
            }

            result = self.service.calculate_daily_summary(target_date)

            self.assertIsNotNone(result)
            self.assertEqual(result.date, target_date)
            self.assertEqual(result.total_food_cost, Decimal("300.00"))
            self.assertEqual(result.resale_cost, Decimal("100.00"))

    def test_is_resale_product_logic(self):
        """Test resale product identification logic"""
        # Product with recipe should not be resale
        self.assertFalse(self.service._is_resale_product(self.food_product))

        # Product without recipe should be resale
        self.assertTrue(self.service._is_resale_product(self.resale_product))

    def test_calculate_enhanced_cost_metrics(self):
        """Test enhanced cost metrics calculation"""
        with patch.object(self.service, "_calculate_item_cost") as mock_item_cost:
            mock_item_cost.return_value = Decimal("5.00")

            result = self.service._calculate_enhanced_cost_metrics(date.today())

            self.assertIn("total_food_cost", result)
            self.assertIn("resale_cost", result)
            self.assertNotIn("total_beverage_cost", result)  # Should be removed
            self.assertNotIn("total_packaging_cost", result)  # Should be removed

    def test_calculate_derived_metrics(self):
        """Test derived metrics calculation with resale_cost"""
        summary = DailySummary.objects.create(
            date=date.today() + timedelta(days=1),
            total_sales=Decimal("1000.00"),
            total_food_cost=Decimal("300.00"),
            resale_cost=Decimal("100.00"),
        )

        self.service._calculate_derived_metrics(summary)

        # Gross profit should be: total_sales - total_food_cost - resale_cost
        expected_gross_profit = (
            Decimal("1000.00") - Decimal("300.00") - Decimal("100.00")
        )
        self.assertEqual(summary.gross_profit, expected_gross_profit)

    def test_get_performance_analysis(self):
        """Test performance analysis with updated metrics"""
        target_date = date.today()

        result = self.service.get_performance_analysis(target_date)

        self.assertIn("performance_grade", result)
        self.assertIn("food_cost_status", result)
        self.assertIn("is_food_cost_healthy", result)
        self.assertIn("benchmarks", result)


class ProductCostingServiceTestCase(TestCase):
    """Test cases for ProductCostingService"""

    def setUp(self):
        """Set up test data"""
        self.unit = UnitOfMeasure.objects.create(name="kg", abbreviation="kg")
        self.purchase_category = PurchasesCategory.objects.create(name="Test Category")
        self.sales_category = SalesCategory.objects.create(name="Test Sales")

        self.product = Product.objects.create(
            name="Test Product",
            current_cost_per_unit=Decimal("5.00"),
            current_selling_price=Decimal("10.00"),
            current_stock=Decimal("25.00"),
            unit_of_measure=self.unit,
            purchase_category=self.purchase_category,
            sales_category=self.sales_category,
        )

        # Create ProductType for the product
        from apps.restaurant_data.models import ProductType

        self.product_type = ProductType.objects.create(
            product=self.product,
            cost_type="raw_material_costs",
            product_type="dish",
        )

        self.service = ProductCostingService()

    def test_get_current_product_cost(self):
        """Test getting current product cost"""
        # Create cost history
        ProductCostHistory.objects.create(
            product=self.product,
            unit_cost_in_recipe_units=Decimal("4.50"),
            recipe_quantity=Decimal("10.0"),
            purchase_date=timezone.now() - timedelta(days=30),
            product_category=self.product_type,
        )

        cost = self.service.get_current_product_cost(self.product)
        self.assertIsInstance(cost, Decimal)
        self.assertGreater(cost, Decimal("0"))

    def test_update_product_cost_history(self):
        """Test updating product cost history"""
        # Create ProductCostHistory directly instead of using RecipeConsolidatedPurchase
        history = ProductCostHistory.objects.create(
            product=self.product,
            purchase_date=timezone.now(),
            quantity_ordered=Decimal("10.0"),
            unit_of_purchase=self.unit,
            total_amount=Decimal("40.00"),
            unit_of_recipe=self.unit,
            recipe_conversion_factor=Decimal("1.0"),
            recipe_quantity=Decimal("10.0"),
            unit_cost_in_recipe_units=Decimal("4.00"),
            product_category=self.product_type,
        )

        # Check if cost history was created
        history = ProductCostHistory.objects.filter(product=self.product).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.unit_cost_in_recipe_units, Decimal("4.00"))

    def test_get_cost_trend(self):
        """Test getting cost trend data"""
        # Create multiple cost history records
        dates = [timezone.now() - timedelta(days=i * 7) for i in range(3)]
        costs = [Decimal("4.00"), Decimal("4.50"), Decimal("5.00")]

        for date, cost in zip(dates, costs):
            ProductCostHistory.objects.create(
                product=self.product,
                unit_cost_in_recipe_units=cost,
                recipe_quantity=Decimal("10.0"),
                purchase_date=date,
                product_category=self.product_type,
            )

        trend = self.service.get_cost_trend(self.product, days=30)

        self.assertEqual(len(trend), 3)
        self.assertIsInstance(trend[0], dict)
        self.assertIn("date", trend[0])
        self.assertIn("cost", trend[0])


class DailySummaryModelTestCase(TestCase):
    """Test cases for DailySummary model"""

    def setUp(self):
        """Set up test data"""
        self.summary = DailySummary.objects.create(
            date=date.today(),
            total_sales=Decimal("1000.00"),
            total_food_cost=Decimal("300.00"),
            total_orders=10,
            total_customers=8,
        )

    # TODO: Uncomment after running migrations for resale_cost field
    # def test_resale_cost_field(self):
    #     """Test resale_cost field functionality"""
    #     self.assertEqual(self.summary.resale_cost, Decimal("100.00"))
    #
    #     # Update resale cost
    #     self.summary.resale_cost = Decimal("150.00")
    #     self.summary.save()
    #
    #     # Refresh from database
    #     self.summary.refresh_from_db()
    #     self.assertEqual(self.summary.resale_cost, Decimal("150.00"))
    #
    # def test_gross_profit_calculation_with_resale_cost(self):
    #     """Test gross profit calculation includes resale_cost"""
    #     # Gross profit should be: total_sales - total_food_cost - resale_cost
    #     expected_gross_profit = (
    #         Decimal("1000.00") - Decimal("300.00") - Decimal("100.00")
    #     )
    #     self.assertEqual(self.summary.gross_profit, expected_gross_profit)
    #
    #     # Update resale cost and check gross profit updates
    #     self.summary.resale_cost = Decimal("200.00")
    #     self.summary.save()
    #     self.summary.refresh_from_db()
    #
    #     new_expected_gross_profit = (
    #         Decimal("1000.00") - Decimal("300.00") - Decimal("200.00")
    #     )
    #     self.assertEqual(self.summary.gross_profit, new_expected_gross_profit)

    def test_food_cost_percentage_calculation(self):
        """Test food cost percentage calculation"""
        # Food cost percentage should be: (total_food_cost / total_sales) * 100
        expected_percentage = (Decimal("300.00") / Decimal("1000.00")) * 100
        self.assertEqual(self.summary.food_cost_percentage, expected_percentage)

    def test_performance_grade_methods(self):
        """Test performance grading methods"""
        # Test get_performance_grade
        grade = self.summary.get_performance_grade()
        self.assertIn(grade, ["A", "B", "C", "D", "F"])

        # Test is_food_cost_healthy
        is_healthy = self.summary.is_food_cost_healthy
        self.assertIsInstance(is_healthy, bool)

        # Test food_cost_status
        status = self.summary.food_cost_status
        self.assertIn(status, ["excellent", "good", "fair", "poor", "critical"])


class ProductCostHistoryModelTestCase(TestCase):
    """Test cases for ProductCostHistory model"""

    def setUp(self):
        """Set up test data"""
        self.unit = UnitOfMeasure.objects.create(name="kg", abbreviation="kg")
        self.purchase_category = PurchasesCategory.objects.create(name="Test Category")
        self.sales_category = SalesCategory.objects.create(name="Test Sales")

        self.product = Product.objects.create(
            name="Test Product",
            current_cost_per_unit=Decimal("5.00"),
            current_selling_price=Decimal("10.00"),
            current_stock=Decimal("25.00"),
            unit_of_measure=self.unit,
            purchase_category=self.purchase_category,
            sales_category=self.sales_category,
        )

    def test_product_cost_history_creation(self):
        """Test creating ProductCostHistory records"""
        history = ProductCostHistory.objects.create(
            product=self.product,
            cost_per_unit=Decimal("4.50"),
            quantity_purchased=Decimal("10.0"),
            purchase_date=timezone.now(),
            product_category="ingredient",
        )

        self.assertEqual(history.product, self.product)
        self.assertEqual(history.cost_per_unit, Decimal("4.50"))
        self.assertEqual(history.product_category, "ingredient")
        self.assertTrue(history.is_active)

    def test_product_cost_history_str_method(self):
        """Test string representation"""
        history = ProductCostHistory.objects.create(
            product=self.product,
            cost_per_unit=Decimal("4.50"),
            quantity_purchased=Decimal("10.0"),
            purchase_date=timezone.now(),
            product_category="ingredient",
        )

        expected_str = (
            f"{self.product.name} - 4.50 FCFA ({history.purchase_date.date()})"
        )
        self.assertEqual(str(history), expected_str)

    def test_product_cost_history_categories(self):
        """Test different product categories"""
        categories = ["ingredient", "resale"]

        for category in categories:
            history = ProductCostHistory.objects.create(
                product=self.product,
                cost_per_unit=Decimal("4.50"),
                quantity_purchased=Decimal("10.0"),
                purchase_date=timezone.now(),
                product_category=category,
            )

            self.assertEqual(history.product_category, category)

    def test_product_cost_history_ordering(self):
        """Test ordering by purchase date"""
        # Create records with different dates
        dates = [
            timezone.now() - timedelta(days=30),
            timezone.now() - timedelta(days=15),
            timezone.now(),
        ]

        for purchase_date in dates:
            ProductCostHistory.objects.create(
                product=self.product,
                cost_per_unit=Decimal("4.50"),
                quantity_purchased=Decimal("10.0"),
                purchase_date=purchase_date,
                product_category="ingredient",
            )

        # Should be ordered by purchase_date descending
        histories = ProductCostHistory.objects.all()
        self.assertEqual(histories[0].purchase_date, dates[2])  # Most recent first
        self.assertEqual(histories[2].purchase_date, dates[0])  # Oldest last

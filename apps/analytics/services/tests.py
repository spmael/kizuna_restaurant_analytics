from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.analytics.models import DailySummary, ProductCostHistory
from apps.analytics.services.ingredient_costing import ProductCostingService
from apps.analytics.services.recipe_costing import RecipeCostingService
from apps.analytics.services.services import DailyAnalyticsService
from apps.recipes.models import ProductCostHistory, Recipe, RecipeIngredient
from apps.restaurant_data.models import (
    Product,
    PurchasesCategory,
    SalesCategory,
    UnitOfMeasure,
)


class DailyAnalyticsServiceIntegrationTestCase(TestCase):
    """Integration tests for DailyAnalyticsService"""

    def setUp(self):
        """Set up comprehensive test data"""
        # Create units
        self.kg_unit = UnitOfMeasure.objects.create(name="Kilogram", abbreviation="kg")
        self.piece_unit = UnitOfMeasure.objects.create(name="Piece", abbreviation="pc")

        # Create categories
        self.purchase_category = PurchasesCategory.objects.create(name="Food Items")
        self.sales_category = SalesCategory.objects.create(name="Food Sales")

        # Create products
        self.rice = Product.objects.create(
            name="Rice",
            current_cost_per_unit=Decimal("2.50"),
            current_selling_price=Decimal("5.00"),
            current_stock=Decimal("100.00"),
            unit_of_measure=self.kg_unit,
            purchase_category=self.purchase_category,
            sales_category=self.sales_category,
        )

        self.water = Product.objects.create(
            name="Bottled Water",
            current_cost_per_unit=Decimal("1.00"),
            current_selling_price=Decimal("2.00"),
            current_stock=Decimal("50.00"),
            unit_of_measure=self.piece_unit,
            purchase_category=self.purchase_category,
            sales_category=self.sales_category,
        )

        self.chicken = Product.objects.create(
            name="Chicken Breast",
            current_cost_per_unit=Decimal("8.00"),
            current_selling_price=Decimal("15.00"),
            current_stock=Decimal("25.00"),
            unit_of_measure=self.kg_unit,
            purchase_category=self.purchase_category,
            sales_category=self.sales_category,
        )

        # Create recipe
        self.recipe = Recipe.objects.create(
            dish_name="Chicken Rice Bowl",
            serving_size=Decimal("2.0"),
            waste_factor_percentage=Decimal("5.00"),
            labour_cost_percentage=Decimal("10.00"),
            target_food_cost_percentage=Decimal("30.00"),
        )

        # Create recipe ingredients
        RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.rice,
            quantity=Decimal("0.5"),
            unit_of_recipe=self.kg_unit,
        )

        RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.chicken,
            quantity=Decimal("0.3"),
            unit_of_recipe=self.kg_unit,
        )

        # Create ProductTypes for products
        from apps.restaurant_data.models import ProductType

        self.rice_type = ProductType.objects.create(
            product=self.rice,
            cost_type="raw_material_costs",
            product_type="dish",
        )
        self.water_type = ProductType.objects.create(
            product=self.water,
            cost_type="raw_material_costs",
            product_type="resale",
        )
        self.chicken_type = ProductType.objects.create(
            product=self.chicken,
            cost_type="raw_material_costs",
            product_type="dish",
        )

        # Create cost history
        ProductCostHistory.objects.create(
            product=self.rice,
            unit_cost_in_recipe_units=Decimal("2.50"),
            recipe_quantity=Decimal("10.0"),
            purchase_date=timezone.now() - timedelta(days=7),
            product_category=self.rice_type,
        )

        ProductCostHistory.objects.create(
            product=self.water,
            unit_cost_in_recipe_units=Decimal("1.00"),
            recipe_quantity=Decimal("50.0"),
            purchase_date=timezone.now() - timedelta(days=3),
            product_category=self.water_type,
        )

        self.service = DailyAnalyticsService()

    def test_full_daily_stats_calculation(self):
        """Test complete daily stats calculation with real data"""
        target_date = date.today()

        # Mock sales data
        with patch.object(self.service, "_get_sales_data") as mock_sales:
            mock_sales.return_value = {
                "total_sales": Decimal("1500.00"),
                "total_orders": 15,
                "total_customers": 12,
                "sales_by_product": {
                    "Chicken Rice Bowl": {"quantity": 10, "revenue": Decimal("800.00")},
                    "Bottled Water": {"quantity": 20, "revenue": Decimal("40.00")},
                },
            }

            result = self.service.calculate_daily_stats(target_date)

            self.assertIsNotNone(result)
            self.assertEqual(result.date, target_date)
            self.assertEqual(result.total_sales, Decimal("1500.00"))
            self.assertEqual(result.total_orders, 15)
            self.assertEqual(result.total_customers, 12)

            # Check that costs are calculated
            self.assertGreater(result.total_food_cost, Decimal("0"))
            self.assertGreater(result.resale_cost, Decimal("0"))

            # Check derived metrics
            self.assertGreater(result.gross_profit, Decimal("0"))
            self.assertGreater(result.food_cost_percentage, Decimal("0"))

    def test_product_categorization_logic(self):
        """Test product categorization between food and resale"""
        # Rice should be food (has recipe)
        self.assertFalse(self.service._is_resale_product(self.rice))

        # Water should be resale (no recipe)
        self.assertTrue(self.service._is_resale_product(self.water))

        # Chicken should be food (has recipe)
        self.assertFalse(self.service._is_resale_product(self.chicken))

    def test_cost_calculation_by_category(self):
        """Test cost calculation separates food and resale costs"""
        target_date = date.today()

        # Mock sales data with both food and resale items
        with patch.object(self.service, "_get_sales_data") as mock_sales:
            mock_sales.return_value = {
                "total_sales": Decimal("1000.00"),
                "total_orders": 10,
                "total_customers": 8,
                "sales_by_product": {
                    "Chicken Rice Bowl": {"quantity": 5, "revenue": Decimal("400.00")},
                    "Bottled Water": {"quantity": 10, "revenue": Decimal("20.00")},
                },
            }

            result = self.service.calculate_daily_stats(target_date)

            # Both food and resale costs should be calculated
            self.assertGreater(result.total_food_cost, Decimal("0"))
            self.assertGreater(result.resale_cost, Decimal("0"))

            # Gross profit should account for both costs
            expected_gross_profit = (
                result.total_sales - result.total_food_cost - result.resale_cost
            )
            self.assertEqual(result.gross_profit, expected_gross_profit)

    def test_performance_analysis_with_resale_costs(self):
        """Test performance analysis includes resale cost considerations"""
        # Create a daily summary with resale costs
        summary = DailySummary.objects.create(
            date=date.today(),
            total_sales=Decimal("2000.00"),
            total_food_cost=Decimal("600.00"),
            total_orders=20,
            total_customers=15,
        )

        analysis = self.service.get_performance_analysis(date.today())

        self.assertIn("overall_grade", analysis)
        self.assertIn("food_cost_grade", analysis)
        self.assertIn("sales_grade", analysis)
        self.assertIn("profitability_grade", analysis)

        # All grades should be valid
        valid_grades = ["A", "B", "C", "D", "F"]
        self.assertIn(analysis["overall_grade"], valid_grades)


class ProductCostingServiceIntegrationTestCase(TestCase):
    """Integration tests for ProductCostingService"""

    def setUp(self):
        """Set up test data"""
        self.unit = UnitOfMeasure.objects.create(name="kg", abbreviation="kg")

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

    def test_weighted_average_cost_calculation(self):
        """Test weighted average cost calculation with multiple purchases"""
        # Create multiple cost history records with different costs
        costs_data = [
            (
                Decimal("4.00"),
                Decimal("10.0"),
                30,
            ),  # 4.00 per unit, 10 units, 30 days ago
            (
                Decimal("4.50"),
                Decimal("15.0"),
                15,
            ),  # 4.50 per unit, 15 units, 15 days ago
            (Decimal("5.00"), Decimal("20.0"), 1),  # 5.00 per unit, 20 units, 1 day ago
        ]

        for cost, quantity, days_ago in costs_data:
            ProductCostHistory.objects.create(
                product=self.product,
                unit_cost_in_recipe_units=cost,
                recipe_quantity=quantity,
                purchase_date=timezone.now() - timedelta(days=days_ago),
                product_category=self.product_type,
            )

        # Calculate weighted average cost
        current_cost = self.service.get_current_product_cost(self.product)

        # Should be a weighted average, not just the latest cost
        self.assertIsInstance(current_cost, Decimal)
        self.assertGreater(current_cost, Decimal("4.00"))
        self.assertLess(current_cost, Decimal("5.00"))

    def test_cost_trend_analysis(self):
        """Test cost trend analysis over time"""
        # Create cost history over several months
        base_date = timezone.now() - timedelta(days=90)
        costs = [
            Decimal("4.00"),
            Decimal("4.25"),
            Decimal("4.50"),
            Decimal("4.75"),
            Decimal("5.00"),
        ]

        for i, cost in enumerate(costs):
            ProductCostHistory.objects.create(
                product=self.product,
                unit_cost_in_recipe_units=cost,
                recipe_quantity=Decimal("10.0"),
                purchase_date=base_date + timedelta(days=i * 20),
                product_category=self.product_type,
            )

        # Get cost trend
        trend = self.service.get_cost_trend(self.product, days=90)

        self.assertEqual(len(trend), 5)

        # Check trend data structure
        for data_point in trend:
            self.assertIn("date", data_point)
            self.assertIn("cost", data_point)
            self.assertIn("quantity", data_point)
            self.assertIsInstance(data_point["cost"], float)
            self.assertIsInstance(data_point["quantity"], float)

    def test_bulk_cost_history_update(self):
        """Test bulk update of cost history from consolidated purchases"""
        # Create multiple consolidated purchases
        purchases_data = [
            (Decimal("4.00"), Decimal("10.0"), 30),
            (Decimal("4.50"), Decimal("15.0"), 15),
            (Decimal("5.00"), Decimal("20.0"), 1),
        ]

        for cost, quantity, days_ago in purchases_data:
            ProductCostHistory.objects.create(
                product=self.product,
                purchase_date=timezone.now() - timedelta(days=days_ago),
                quantity_ordered=quantity,
                unit_of_purchase=self.unit,
                total_amount=cost * quantity,
                unit_cost_in_recipe_units=cost,
                recipe_quantity=quantity,
                unit_of_recipe=self.unit,
                product_category=self.product_type,
            )

        # Perform bulk update
        result = self.service.bulk_update_product_cost_history()

        self.assertIn("created", result)
        self.assertIn("updated", result)
        self.assertGreater(result["created"], 0)

        # Check that cost history records were created
        history_count = ProductCostHistory.objects.filter(product=self.product).count()
        self.assertGreater(history_count, 0)


class RecipeCostingServiceIntegrationTestCase(TestCase):
    """Integration tests for RecipeCostingService"""

    def setUp(self):
        """Set up test data"""
        self.kg_unit = UnitOfMeasure.objects.create(name="Kilogram", abbreviation="kg")
        self.piece_unit = UnitOfMeasure.objects.create(name="Piece", abbreviation="pc")

        # Create ingredients
        self.rice = Product.objects.create(
            name="Rice",
            current_cost_per_unit=Decimal("2.50"),
            current_selling_price=Decimal("5.00"),
            current_stock=Decimal("100.00"),
            unit_of_measure=self.kg_unit,
            purchase_category=self.purchase_category,
            sales_category=self.sales_category,
        )

        self.chicken = Product.objects.create(
            name="Chicken",
            current_cost_per_unit=Decimal("8.00"),
            current_selling_price=Decimal("15.00"),
            current_stock=Decimal("25.00"),
            unit_of_measure=self.kg_unit,
            purchase_category=self.purchase_category,
            sales_category=self.sales_category,
        )

        # Create recipe
        self.recipe = Recipe.objects.create(
            dish_name="Chicken Rice",
            serving_size=Decimal("2.0"),
            waste_factor_percentage=Decimal("5.00"),
            labour_cost_percentage=Decimal("10.00"),
            target_food_cost_percentage=Decimal("30.00"),
        )

        # Create recipe ingredients
        RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.rice,
            quantity=Decimal("0.5"),
            unit_of_recipe=self.kg_unit,
        )

        RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.chicken,
            quantity=Decimal("0.3"),
            unit_of_recipe=self.kg_unit,
        )

        # Create ProductTypes for products
        from apps.restaurant_data.models import ProductType

        self.rice_type = ProductType.objects.create(
            product=self.rice,
            cost_type="raw_material_costs",
            product_type="dish",
        )
        self.chicken_type = ProductType.objects.create(
            product=self.chicken,
            cost_type="raw_material_costs",
            product_type="dish",
        )

        # Create cost history
        ProductCostHistory.objects.create(
            product=self.rice,
            unit_cost_in_recipe_units=Decimal("2.50"),
            recipe_quantity=Decimal("10.0"),
            purchase_date=timezone.now() - timedelta(days=7),
            product_category=self.rice_type,
        )

        ProductCostHistory.objects.create(
            product=self.chicken,
            unit_cost_in_recipe_units=Decimal("8.00"),
            recipe_quantity=Decimal("5.0"),
            purchase_date=timezone.now() - timedelta(days=3),
            product_category=self.chicken_type,
        )

        self.service = RecipeCostingService()

    def test_recipe_cost_calculation(self):
        """Test complete recipe cost calculation"""
        cost_data = self.service.calculate_recipe_cost(self.recipe)

        # Check cost breakdown
        self.assertIn("total_ingredient_cost", cost_data)
        self.assertIn("waste_cost", cost_data)
        self.assertIn("labor_cost", cost_data)
        self.assertIn("total_recipe_cost", cost_data)
        self.assertIn("base_cost_per_portion", cost_data)
        self.assertIn("total_cost_per_portion", cost_data)
        self.assertIn("suggested_selling_price", cost_data)

        # Check calculations
        self.assertGreater(cost_data["total_ingredient_cost"], Decimal("0"))
        self.assertGreater(cost_data["waste_cost"], Decimal("0"))
        self.assertGreater(cost_data["labor_cost"], Decimal("0"))
        self.assertGreater(cost_data["total_cost_per_portion"], Decimal("0"))
        self.assertGreater(cost_data["suggested_selling_price"], Decimal("0"))

    def test_recipe_cost_update(self):
        """Test updating recipe costs"""
        # Update recipe costs
        self.service.update_recipe_costs(self.recipe)

        # Refresh recipe from database
        self.recipe.refresh_from_db()

        # Check that costs were updated
        self.assertGreater(self.recipe.base_food_cost_per_portion, Decimal("0"))
        self.assertGreater(self.recipe.total_cost_per_portion, Decimal("0"))
        self.assertGreater(
            self.recipe.suggested_selling_price_per_portion, Decimal("0")
        )

        # Check that ingredient costs were updated
        for ingredient in self.recipe.ingredients.all():
            self.assertGreater(ingredient.cost_per_unit, Decimal("0"))
            self.assertGreater(ingredient.total_cost, Decimal("0"))
            self.assertGreater(ingredient.cost_per_portion, Decimal("0"))

    def test_recipe_cost_efficiency_analysis(self):
        """Test recipe cost efficiency analysis"""
        # Set actual selling price for efficiency calculation
        self.recipe.actual_selling_price_per_portion = Decimal("25.00")
        self.recipe.save()

        # Update costs
        self.service.update_recipe_costs(self.recipe)

        # Get efficiency analysis
        efficient_recipes = self.service.get_recipes_by_cost_efficiency(limit=5)

        # Should return list of recipes with efficiency data
        self.assertIsInstance(efficient_recipes, list)

        if efficient_recipes:
            recipe_data = efficient_recipes[0]
            self.assertIn("recipe", recipe_data)
            self.assertIn("profit_margin", recipe_data)
            self.assertIn("profit_per_portion", recipe_data)
            self.assertIsInstance(recipe_data["profit_margin"], Decimal)
            self.assertIsInstance(recipe_data["profit_per_portion"], Decimal)

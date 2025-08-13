import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from django.db.models import Avg, Count, Sum
from django.utils import timezone

from apps.analytics.models import DailySummary
from apps.recipes.models import Recipe
from apps.restaurant_data.models import Product, Sales

from .ingredient_costing import ProductCostingService

# Import the new costing services
from .recipe_costing import RecipeCostingService

logger = logging.getLogger(__name__)


class DailyAnalyticsService:
    """Service to calculate daily restaurant statistics"""

    # Industry benchmarks for Cameroon restaurant market
    RESTAURANT_BENCHMARKS = {
        "food_cost_percentage": {
            "excellent": (20, 25),  # Under 25%
            "good": (25, 30),  # 25-30%
            "acceptable": (30, 35),  # 30-35%
            "poor": (35, 100),  # Over 35%
        },
        "average_order_value": {
            "cameroon_casual": (2000, 8000),  # 2,000-8,000 FCFA
            "cameroon_upscale": (8000, 25000),  # 8,000-25,000 FCFA
        },
        "covers_per_day": {
            "small_restaurant": (50, 150),  # 50-150 customers
            "medium_restaurant": (150, 300),  # 150-300 customers
            "large_restaurant": (300, 500),  # 300+ customers
        },
        "payment_methods_cameroon": {
            "cash_percentage": (60, 80),  # 60-80% still cash
            "mobile_money_percentage": (15, 30),  # Growing rapidly
            "card_percentage": (5, 15),  # Still limited
        },
    }

    def __init__(self):
        self.errors = []
        self.warnings = []
        # Initialize costing services
        self.recipe_costing_service = RecipeCostingService()
        self.product_costing_service = ProductCostingService()

    def calculate_daily_summary(self, target_date: date = None) -> DailySummary:
        """Calculate daily summary statistics for a given date"""

        if target_date is None:
            target_date = date.today() - timedelta(days=1)  # default to yesterday

        logger.info(f"Calculating daily summary for {target_date}")

        # Check if summary already exists
        existing_summary, created = DailySummary.objects.get_or_create(
            date=target_date, defaults=self._get_default_summary_data()
        )

        if not created:
            logger.info(f"Daily summary already exists for {target_date}")

        # Calculate sales metrics
        sales_data = self._calculate_sales_metrics(target_date)

        # Calculate enhanced cost metrics using recipe costing with confidence
        cost_data = self._calculate_enhanced_cost_metrics_with_confidence(target_date)

        # Calculate payment method breakdown
        payment_data = self._calculate_payment_methods(target_date)

        # Calculate time-based metrics
        time_data = self._calculate_time_based_metrics(target_date)

        # Update the summary with the calculated metrics
        for field, value in {
            **sales_data,
            **cost_data,
            **payment_data,
            **time_data,
        }.items():
            setattr(existing_summary, field, value)

        # Calculate derived metrics
        existing_summary = self._calculate_derived_metrics(existing_summary)

        # Before saving, validate all calculated values
        calculated_values = {
            "total_sales": existing_summary.total_sales,
            "total_food_cost": existing_summary.total_food_cost,
            "resale_cost": existing_summary.resale_cost,
            "gross_profit": existing_summary.gross_profit,
            "food_cost_percentage": existing_summary.food_cost_percentage,
        }

        print(f"\n=== VALIDATING CALCULATED VALUES FOR {target_date} ===")
        for key, value in calculated_values.items():
            if isinstance(value, Decimal):
                if value.is_nan() or value.is_infinite():
                    print(f"❌ Invalid {key}: {value}")
                    setattr(existing_summary, key, Decimal("0.00"))
                elif abs(value) > Decimal("999999999999999"):
                    print(f"❌ Too large {key}: {value}")
                    setattr(existing_summary, key, Decimal("999999999999999.00"))
                else:
                    print(f"✅ Valid {key}: {value}")

        existing_summary.save()

        logger.info(
            f"Daily summary calculated and saved for {target_date}: "
            f"Sales: {existing_summary.total_sales}, "
            f"Orders: {existing_summary.total_orders}, "
            f"Food Cost: {existing_summary.total_food_cost}, "
        )

        return existing_summary

    def _calculate_sales_metrics(self, target_date: date) -> Dict:
        """Calculate sales metrics for a given date"""

        # Get all sales for the given date
        daily_sales = Sales.objects.filter(sale_date=target_date)

        # Basic aggregations
        sales_agg = daily_sales.aggregate(
            total_sales=Sum("total_sale_price"),
            total_orders=Count(
                "order_number", distinct=True
            ),  # Fixed: count unique order numbers
            total_customers=Count(
                "order_number", distinct=True
            ),  # Fixed: count unique orders as customers (since customer field is null)
            total_items_sold=Sum("quantity_sold"),
        )

        # Calculate average order value
        total_sales = sales_agg["total_sales"] or Decimal("0")
        total_orders = sales_agg["total_orders"] or 0
        average_order_value = (
            total_sales / total_orders if total_orders > 0 else Decimal("0")
        )

        # Round to 2 decimal places to prevent excessive precision
        from decimal import ROUND_HALF_UP

        total_sales_rounded = total_sales.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        average_order_value_rounded = average_order_value.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return {
            "total_sales": total_sales_rounded,
            "total_orders": total_orders,
            "total_customers": sales_agg["total_customers"] or 0,
            "average_order_value": average_order_value_rounded,
            "total_items_sold": sales_agg["total_items_sold"] or 0,
        }

    def _calculate_enhanced_cost_metrics(self, target_date: date) -> Dict:
        """Calculate enhanced cost metrics using recipe costing and product costing"""

        print(f"\n=== DEBUGGING COST CALCULATION FOR {target_date} ===")

        # Get all sales for the given date
        daily_sales = Sales.objects.filter(sale_date=target_date)

        total_food_cost = Decimal("0")
        total_resale_cost = Decimal("0")

        print(f"Processing {daily_sales.count()} sales records...")

        # Calculate costs for each sold item
        for i, sale in enumerate(daily_sales):
            item_cost = self._calculate_item_cost(sale, target_date)

            print(
                f"Sale {i+1}: {sale.product.name} - Qty: {sale.quantity_sold}, Cost: {item_cost}"
            )

            # Categorize costs based on product type
            if self._is_resale_product(sale.product):
                total_resale_cost += item_cost
                print(f"  → Added to resale_cost (total now: {total_resale_cost})")
            else:
                total_food_cost += item_cost
                print(f"  → Added to food_cost (total now: {total_food_cost})")

        print(f"\nRaw total_food_cost before processing: {total_food_cost}")
        print(f"Raw resale_cost before processing: {total_resale_cost}")

        # Round to 2 decimal places to match database constraints
        from decimal import ROUND_HALF_UP

        total_food_cost_rounded = total_food_cost.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total_resale_cost_rounded = total_resale_cost.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        print(f"Final total_food_cost: {total_food_cost_rounded}")
        print(f"Final resale_cost: {total_resale_cost_rounded}")

        return {
            "total_food_cost": total_food_cost_rounded,
            "resale_cost": total_resale_cost_rounded,
        }

    def _calculate_enhanced_cost_metrics_with_confidence(
        self, target_date: date
    ) -> Dict:
        """
        Enhanced version of _calculate_enhanced_cost_metrics
        Now returns both conservative and estimated costs with confidence
        """

        daily_sales = Sales.objects.filter(sale_date=target_date)

        conservative_food_cost = Decimal("0")
        estimated_food_cost = Decimal("0")
        total_resale_cost = Decimal("0")

        total_missing = 0
        total_estimated = 0
        confidence_scores = []

        print(f"\n=== ENHANCED COST CALCULATION FOR {target_date} ===")

        for i, sale in enumerate(daily_sales):
            if self._is_resale_product(sale.product):
                # Resale products - use existing logic
                item_cost = self._calculate_product_based_cost(
                    sale.product, sale.quantity_sold, target_date
                )
                total_resale_cost += item_cost
                confidence_scores.append(100)  # Resale costs are always certain

            else:
                # Recipe products - use enhanced dual calculation
                recipe = self._find_recipe_for_product(sale.product)
                if recipe:
                    dual_cost = self.recipe_costing_service.calculate_dual_recipe_cost(
                        recipe, target_date
                    )

                    # Calculate costs for quantity sold
                    conservative_cost = (
                        dual_cost["conservative"]["total_cost_per_portion"]
                        * sale.quantity_sold
                    )
                    estimated_cost = (
                        dual_cost["estimated"]["total_cost_per_portion"]
                        * sale.quantity_sold
                    )

                    conservative_food_cost += conservative_cost
                    estimated_food_cost += estimated_cost

                    # Track confidence metrics
                    conf_data = dual_cost["confidence_data"]
                    total_missing += conf_data["missing_ingredients_count"]
                    total_estimated += conf_data["estimated_ingredients_count"]
                    confidence_scores.append(conf_data["data_completeness_percentage"])

                    print(f"Sale {i+1}: {sale.product.name}")
                    print(f"  Conservative: {conservative_cost}")
                    print(f"  Estimated: {estimated_cost}")
                    print(f"  Confidence: {conf_data['confidence_level']}")
                else:
                    # Fallback to existing product-based calculation
                    item_cost = self._calculate_product_based_cost(
                        sale.product, sale.quantity_sold, target_date
                    )
                    conservative_food_cost += item_cost
                    estimated_food_cost += item_cost
                    confidence_scores.append(50)  # Medium confidence for fallback

        # Calculate overall confidence
        overall_completeness = (
            sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        )

        if overall_completeness >= 90:
            overall_confidence = "HIGH"
        elif overall_completeness >= 70:
            overall_confidence = "MEDIUM"
        elif overall_completeness >= 50:
            overall_confidence = "LOW"
        else:
            overall_confidence = "VERY_LOW"

        # Round results
        from decimal import ROUND_HALF_UP

        return {
            "total_food_cost": estimated_food_cost.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            "total_food_cost_conservative": conservative_food_cost.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            "resale_cost": total_resale_cost.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            "cogs_confidence_level": overall_confidence,
            "data_completeness_percentage": overall_completeness,
            "missing_ingredients_count": total_missing,
            "estimated_ingredients_count": total_estimated,
        }

    def _calculate_item_cost(self, sale: Sales, target_date: date) -> Decimal:
        """Calculate the actual cost of a sold item using recipe costing"""

        # Try to find a recipe for this product
        recipe = self._find_recipe_for_product(sale.product)

        if recipe:
            # Use recipe costing
            return self._calculate_recipe_based_cost(
                recipe, sale.quantity_sold, target_date
            )
        else:
            # Fall back to product costing for raw ingredients
            return self._calculate_product_based_cost(
                sale.product, sale.quantity_sold, target_date
            )

    def _find_recipe_for_product(self, product: Product) -> Optional[Recipe]:
        """Find a recipe that produces this product"""

        try:
            # First try exact match
            exact_match = Recipe.objects.filter(
                dish_name=product.name, is_active=True
            ).first()
            if exact_match:
                return exact_match

            # Then try exact substring match (e.g., "Poulet Braisé (Quartier)" should match "Poulet Braisé (Quartier)")
            exact_substring_match = Recipe.objects.filter(
                dish_name__iexact=product.name, is_active=True
            ).first()
            if exact_substring_match:
                return exact_substring_match

            # Finally try partial match as fallback
            partial_match = Recipe.objects.filter(
                dish_name__icontains=product.name, is_active=True
            ).first()
            if partial_match:
                logger.warning(
                    f"Using partial recipe match for {product.name}: {partial_match.dish_name}"
                )
                return partial_match

            return None

        except Exception as e:
            logger.warning(f"Error finding recipe for product {product.name}: {e}")
            return None

    def _calculate_recipe_based_cost(
        self, recipe: Recipe, quantity_sold: Decimal, target_date: date
    ) -> Decimal:
        """Calculate cost based on recipe costing"""

        try:
            print(f"  Recipe costing for: {recipe.dish_name}")

            # Get current recipe cost calculation
            cost_data = self.recipe_costing_service.calculate_recipe_cost(
                recipe, target_date
            )

            # Calculate total cost for the quantity sold
            cost_per_portion = cost_data["total_cost_per_portion"]
            total_cost = cost_per_portion * quantity_sold

            print(f"    Cost per portion: {cost_per_portion}")
            print(f"    Quantity sold: {quantity_sold}")
            print(f"    Total cost: {total_cost}")

            # Round to 2 decimal places to prevent excessive precision
            from decimal import ROUND_HALF_UP

            rounded_cost = total_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            print(f"    Rounded cost: {rounded_cost}")

            return rounded_cost

        except Exception as e:
            logger.error(f"Error calculating recipe cost for {recipe.dish_name}: {e}")
            print(f"    ❌ Recipe cost error: {e}")
            # Fall back to ingredient costing
            return self._calculate_ingredient_based_cost(
                recipe.ingredients.first().ingredient, quantity_sold, target_date
            )

    def _calculate_ingredient_based_cost(
        self, product: Product, quantity_sold: Decimal, target_date: date
    ) -> Decimal:
        """Calculate cost based on ingredient costing as fallback"""
        try:
            # Get current product cost
            cost_per_unit = self.product_costing_service.get_current_product_cost(
                product, target_date
            )
            # Calculate total cost
            total_cost = cost_per_unit * quantity_sold

            # Round to 2 decimal places to prevent excessive precision
            from decimal import ROUND_HALF_UP

            return total_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except Exception as e:
            logger.error(f"Error calculating ingredient cost for {product.name}: {e}")
            # Fall back to product's current cost
            total_cost = product.current_cost_per_unit * quantity_sold

            # Round to 2 decimal places to prevent excessive precision
            from decimal import ROUND_HALF_UP

            return total_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _calculate_product_based_cost(
        self, product: Product, quantity_sold: Decimal, target_date: date
    ) -> Decimal:
        """Calculate cost based on product costing"""

        try:
            print(f"  Product costing for: {product.name}")

            # Get current product cost
            cost_per_unit = self.product_costing_service.get_current_product_cost(
                product, target_date
            )

            # Calculate total cost
            total_cost = cost_per_unit * quantity_sold

            print(f"    Cost per unit: {cost_per_unit}")
            print(f"    Quantity sold: {quantity_sold}")
            print(f"    Total cost: {total_cost}")

            # Round to 2 decimal places to prevent excessive precision
            from decimal import ROUND_HALF_UP

            rounded_cost = total_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            print(f"    Rounded cost: {rounded_cost}")

            return rounded_cost

        except Exception as e:
            logger.error(f"Error calculating product cost for {product.name}: {e}")
            print(f"    ❌ Product cost error: {e}")
            # Fall back to product's current cost
            total_cost = product.current_cost_per_unit * quantity_sold

            print(
                f"    Fallback - Current cost per unit: {product.current_cost_per_unit}"
            )
            print(f"    Fallback - Total cost: {total_cost}")

            # Round to 2 decimal places to prevent excessive precision
            from decimal import ROUND_HALF_UP

            rounded_cost = total_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            print(f"    Fallback - Rounded cost: {rounded_cost}")

            return rounded_cost

    def _is_resale_product(self, product: Product) -> bool:
        """Check if product is a resale item (bought and sold directly)"""
        from apps.restaurant_data.models import ProductType

        # Get the product type
        product_type = ProductType.objects.filter(product=product).first()

        if not product_type:
            # If no product type is set, fall back to recipe-based logic
            from apps.recipes.models import Recipe

            has_recipe = Recipe.objects.filter(
                dish_name__icontains=product.name, is_active=True
            ).exists()
            return not has_recipe

        # Use ProductType categorization
        return product_type.product_type == "resale"

    def _calculate_payment_methods(self, target_date: date) -> Dict:
        """Calculate payment method breakdown"""
        # Note: This is a placeholder since the Sales model doesn't have payment method field yet
        # In a real implementation, you would query based on payment_method field

        daily_sales = Sales.objects.filter(sale_date=target_date)
        total_sales = daily_sales.aggregate(total=Sum("total_sale_price"))[
            "total"
        ] or Decimal("0")

        # For now, estimate based on Cameroon market averages
        # In production, this should come from actual payment method data
        cash_percentage = Decimal("70")  # 70% cash is typical in Cameroon
        mobile_money_percentage = Decimal("20")  # 20% mobile money
        card_percentage = Decimal("8")  # 8% card
        other_percentage = Decimal("2")  # 2% other

        # Round all payment calculations to 2 decimal places
        from decimal import ROUND_HALF_UP

        return {
            "cash_sales": ((total_sales * cash_percentage) / 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            "mobile_money_sales": (
                (total_sales * mobile_money_percentage) / 100
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "credit_card_sales": ((total_sales * card_percentage) / 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            "other_payment_methods_sales": (
                (total_sales * other_percentage) / 100
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        }

    def _calculate_time_based_metrics(self, target_date: date) -> Dict:
        """Calculate time-based sales breakdown"""
        # Note: This is a placeholder since the Sales model doesn't have time field yet
        # In a real implementation, you would query based on sale_time field

        daily_sales = Sales.objects.filter(sale_date=target_date)
        total_sales = daily_sales.aggregate(total=Sum("total_sale_price"))[
            "total"
        ] or Decimal("0")

        # Estimate based on typical restaurant patterns
        lunch_percentage = Decimal("40")  # 40% lunch sales
        dinner_percentage = Decimal("60")  # 60% dinner sales

        # Round all time-based calculations to 2 decimal places
        from decimal import ROUND_HALF_UP

        return {
            "lunch_sales": ((total_sales * lunch_percentage) / 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            "dinner_sales": ((total_sales * dinner_percentage) / 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            "peak_hour_sales": ((total_sales * Decimal("25")) / 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            "peak_hour_time": None,  # Fixed: was string, model expects TimeField
        }

    def _calculate_derived_metrics(self, summary: DailySummary) -> DailySummary:
        """Calculate derived metrics for a given summary"""

        from decimal import ROUND_HALF_UP

        # Calculate food cost percentage
        if summary.total_sales > 0:
            summary.food_cost_percentage = (
                (summary.total_food_cost / summary.total_sales) * 100
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            summary.food_cost_percentage = Decimal("0")

        # Calculate profit (including resale cost)
        summary.gross_profit = (
            summary.total_sales - summary.total_food_cost - summary.resale_cost
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Calculate gross profit margin
        if summary.total_sales > 0:
            summary.gross_profit_margin = (
                (summary.gross_profit / summary.total_sales) * 100
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            summary.gross_profit_margin = Decimal("0")

        # Calculate average check per person
        if summary.total_customers > 0:
            summary.average_ticket_size = (
                summary.total_sales / summary.total_customers
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            summary.average_ticket_size = Decimal("0")

        # Calculate average items per order
        if summary.total_orders > 0:
            summary.average_items_per_order = (
                summary.total_items_sold / summary.total_orders
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            summary.average_items_per_order = Decimal("0")

        # Calculate sales per staff (if staff count is available)
        if summary.staff_count > 0:
            summary.sales_per_staff = (
                summary.total_sales / summary.staff_count
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            summary.sales_per_staff = Decimal("0")

        return summary

    def _get_default_summary_data(self) -> Dict:
        """Get default summary data for a new summary"""

        return {
            "total_sales": Decimal("0"),
            "total_orders": 0,
            "total_customers": 0,
            "average_order_value": Decimal("0"),
            "average_ticket_size": Decimal("0"),  # Fixed: was average_check_per_person
            "total_food_cost": Decimal("0"),
            "resale_cost": Decimal("0"),
            "food_cost_percentage": Decimal("0"),
            "gross_profit": Decimal("0"),
            "gross_profit_margin": Decimal("0"),
            "total_items_sold": 0,
            "average_items_per_order": Decimal("0"),
            "cash_sales": Decimal("0"),
            "credit_card_sales": Decimal("0"),  # Fixed: was card_sales
            "mobile_money_sales": Decimal("0"),
            "other_payment_methods_sales": Decimal(
                "0"
            ),  # Fixed: was other_payment_sales
            "lunch_sales": Decimal("0"),
            "dinner_sales": Decimal("0"),
            "peak_hour_sales": Decimal("0"),
            "peak_hour_time": None,  # Fixed: was empty string
            "waste_cost": Decimal("0"),
            "comps_and_discounts": Decimal("0"),
            "staff_count": 0,
            "sales_per_staff": Decimal("0"),
            "dine_in_orders": 0,
            "take_out_orders": 0,  # Fixed: was takeaway_orders
            "delivery_orders": 0,
        }

    def calculate_date_range_summaries(
        self, start_date: date, end_date: date
    ) -> List[DailySummary]:
        """Calculate daily summaries for a given date range"""

        summaries = []
        current_date = start_date

        while current_date <= end_date:
            try:
                summary = self.calculate_daily_summary(current_date)
                summaries.append(summary)
            except Exception as e:
                error_msg = f"Error calculating summary for {current_date}: {str(e)}"
                self.errors.append(error_msg)
                logger.error(error_msg)

            current_date += timedelta(days=1)

        return summaries

    def get_sales_by_product(self, target_date: date) -> List[Dict]:
        """Get sales breakdown by product for a specific date"""

        product_sales = (
            Sales.objects.filter(sale_date=target_date)
            .values("product__name")
            .annotate(
                total_quantity=Sum("quantity_sold"),
                total_revenue=Sum("total_sale_price"),
                average_price=Avg("unit_sale_price"),
            )
            .order_by("-total_revenue")
        )

        return list(product_sales)

    def get_weekly_trends(self, end_date: date = None) -> Dict:
        """Get 7-day trend data"""

        if end_date is None:
            end_date = date.today() - timedelta(days=1)

        start_date = end_date - timedelta(days=6)  # 7 days total

        weekly_data = (
            DailySummary.objects.filter(date__range=[start_date, end_date])
            .order_by("date")
            .values("date", "total_sales", "total_orders", "food_cost_percentage")
        )

        return {
            "period": f"{start_date} to {end_date}",
            "daily_data": list(weekly_data),
        }

    # === NEW ANALYSIS METHODS ===

    def get_performance_analysis(self, target_date: date) -> Dict:
        """Get comprehensive performance analysis for a date"""

        summary = DailySummary.objects.filter(date=target_date).first()
        if not summary:
            return {"error": "No summary found for this date"}

        return {
            "date": target_date,
            "performance_grade": summary.get_performance_grade(),
            "food_cost_status": summary.food_cost_status,
            "is_food_cost_healthy": summary.is_food_cost_healthy,
            "cash_percentage": summary.cash_percentage,
            "digital_payment_percentage": summary.digital_payment_percentage,
            "benchmarks": self._get_benchmark_comparison(summary),
            "insights": self._generate_insights(summary),
        }

    def _get_benchmark_comparison(self, summary: DailySummary) -> Dict:

        benchmarks = {}

        # Food cost comparison
        food_cost = float(summary.food_cost_percentage)
        if food_cost <= 25:
            benchmarks["food_cost"] = "excellent"
        elif food_cost <= 30:
            benchmarks["food_cost"] = "good"
        elif food_cost <= 35:
            benchmarks["food_cost"] = "acceptable"
        else:
            benchmarks["food_cost"] = "needs_attention"

        # Average order value comparison
        aov = float(summary.average_order_value)
        if 2000 <= aov <= 8000:
            benchmarks["average_order_value"] = "cameroon_casual"
        elif 8000 <= aov <= 25000:
            benchmarks["average_order_value"] = "cameroon_upscale"
        else:
            benchmarks["average_order_value"] = "outside_range"

        # Customer count comparison
        customers = summary.total_customers
        if 50 <= customers <= 150:
            benchmarks["customer_volume"] = "small_restaurant"
        elif 150 <= customers <= 300:
            benchmarks["customer_volume"] = "medium_restaurant"
        elif customers > 300:
            benchmarks["customer_volume"] = "large_restaurant"
        else:
            benchmarks["customer_volume"] = "very_small"

        return benchmarks

    def _generate_insights(self, summary: DailySummary) -> List[str]:

        insights = []

        # Food cost insights
        if summary.food_cost_percentage > 35:
            insights.append(
                "Food cost is above industry standard (35%). Consider reviewing supplier prices or menu pricing."
            )
        elif summary.food_cost_percentage < 20:
            insights.append(
                "Food cost is very low. This could indicate underpricing or quality issues."
            )

        # Payment method insights
        if summary.cash_percentage > 80:
            insights.append(
                "High cash percentage. Consider promoting digital payment methods for better tracking."
            )

        # Revenue insights
        if summary.total_sales == 0:
            insights.append("No sales recorded for this day. Verify data entry.")

        # Customer insights
        if summary.total_customers > 0 and summary.average_ticket_size < 2000:
            insights.append(
                "Low average check per person. Consider upselling strategies."
            )

        return insights

    def get_monthly_performance_report(self, year: int, month: int) -> Dict:

        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        summaries = DailySummary.objects.filter(
            date__range=[start_date, end_date]
        ).order_by("date")

        if not summaries.exists():
            return {"error": "No data found for this month"}

        # Calculate monthly totals
        monthly_totals = summaries.aggregate(
            total_sales=Sum("total_sales"),
            total_orders=Sum("total_orders"),
            total_customers=Sum("total_customers"),
            total_food_cost=Sum("total_food_cost"),
            avg_food_cost_pct=Avg("food_cost_percentage"),
            avg_order_value=Avg("average_order_value"),
        )

        # Calculate averages
        total_days = summaries.count()
        avg_daily_sales = (
            monthly_totals["total_sales"] / total_days if total_days > 0 else 0
        )
        avg_daily_orders = (
            monthly_totals["total_orders"] / total_days if total_days > 0 else 0
        )

        return {
            "period": f"{year}-{month:02d}",
            "total_days": total_days,
            "monthly_totals": monthly_totals,
            "daily_averages": {
                "avg_daily_sales": avg_daily_sales,
                "avg_daily_orders": avg_daily_orders,
            },
            "performance_summary": self._get_monthly_performance_summary(summaries),
        }

    def _get_monthly_performance_summary(self, summaries) -> Dict:

        # Count days by performance grade
        grade_counts = {}
        for summary in summaries:
            grade = summary.get_performance_grade()
            grade_counts[grade] = grade_counts.get(grade, 0) + 1

        # Find best and worst days
        best_day = max(summaries, key=lambda x: x.total_sales, default=None)
        worst_day = min(summaries, key=lambda x: x.total_sales, default=None)

        return {
            "grade_distribution": grade_counts,
            "best_day": (
                {
                    "date": best_day.date,
                    "sales": best_day.total_sales,
                    "orders": best_day.total_orders,
                }
                if best_day
                else None
            ),
            "worst_day": (
                {
                    "date": worst_day.date,
                    "sales": worst_day.total_sales,
                    "orders": worst_day.total_orders,
                }
                if worst_day
                else None
            ),
        }

    def get_payment_method_analysis(self, start_date: date, end_date: date) -> Dict:

        summaries = DailySummary.objects.filter(
            date__range=[start_date, end_date]
        ).order_by("date")

        payment_totals = summaries.aggregate(
            total_cash=Sum("cash_sales"),
            total_card=Sum("credit_card_sales"),
            total_mobile_money=Sum("mobile_money_sales"),
            total_other=Sum("other_payment_methods_sales"),
            total_sales=Sum("total_sales"),
        )

        total_sales = payment_totals["total_sales"] or Decimal("0")

        if total_sales > 0:
            percentages = {
                "cash": (payment_totals["total_cash"] / total_sales) * 100,
                "card": (payment_totals["total_card"] / total_sales) * 100,
                "mobile_money": (payment_totals["total_mobile_money"] / total_sales)
                * 100,
                "other": (payment_totals["total_other"] / total_sales) * 100,
            }
        else:
            percentages = {"cash": 0, "card": 0, "mobile_money": 0, "other": 0}

        return {
            "period": f"{start_date} to {end_date}",
            "totals": payment_totals,
            "percentages": percentages,
            "benchmark_comparison": self._compare_payment_methods_to_benchmarks(
                percentages
            ),
        }

    def _compare_payment_methods_to_benchmarks(self, percentages: Dict) -> Dict:

        benchmarks = self.RESTAURANT_BENCHMARKS["payment_methods_cameroon"]

        comparison = {}

        # Cash comparison
        cash_pct = float(percentages["cash"])
        if (
            benchmarks["cash_percentage"][0]
            <= cash_pct
            <= benchmarks["cash_percentage"][1]
        ):
            comparison["cash"] = "within_benchmark"
        elif cash_pct > benchmarks["cash_percentage"][1]:
            comparison["cash"] = "above_benchmark"
        else:
            comparison["cash"] = "below_benchmark"

        # Mobile money comparison
        mobile_pct = float(percentages["mobile_money"])
        if (
            benchmarks["mobile_money_percentage"][0]
            <= mobile_pct
            <= benchmarks["mobile_money_percentage"][1]
        ):
            comparison["mobile_money"] = "within_benchmark"
        elif mobile_pct > benchmarks["mobile_money_percentage"][1]:
            comparison["mobile_money"] = "above_benchmark"
        else:
            comparison["mobile_money"] = "below_benchmark"

        return comparison

    # === NEW RECIPE COSTING INTEGRATION METHODS ===

    def get_recipe_cost_analysis(self, target_date: date = None) -> Dict:
        """Get recipe cost analysis for a specific date"""

        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        # Get all active recipes
        active_recipes = Recipe.objects.filter(is_active=True)

        recipe_costs = []
        total_recipe_cost = Decimal("0")

        for recipe in active_recipes:
            try:
                cost_data = self.recipe_costing_service.calculate_recipe_cost(
                    recipe, target_date
                )
                recipe_costs.append(
                    {
                        "recipe": recipe,
                        "cost_data": cost_data,
                        "food_cost_percentage": (
                            (
                                cost_data["total_cost_per_portion"]
                                / recipe.actual_selling_price_per_portion
                                * 100
                            )
                            if recipe.actual_selling_price_per_portion
                            else None
                        ),
                    }
                )
                total_recipe_cost += cost_data["total_cost_per_portion"]
            except Exception as e:
                logger.error(
                    f"Error calculating cost for recipe {recipe.dish_name}: {e}"
                )

        return {
            "date": target_date,
            "total_recipes": len(recipe_costs),
            "total_recipe_cost": total_recipe_cost,
            "recipe_costs": recipe_costs,
        }

    def get_product_cost_trends(self, days: int = 30) -> Dict:
        """Get product cost trends over time"""

        # Get all products that are ingredients
        products = Product.objects.filter(
            purchase_category__name__icontains="ingredient"
        )

        product_trends = {}

        for product in products[:20]:  # Limit to first 20 for performance
            try:
                trend_data = self.product_costing_service.get_cost_trend(product, days)
                if trend_data:
                    product_trends[product.name] = trend_data
            except Exception as e:
                logger.error(f"Error getting cost trend for {product.name}: {e}")

        return {
            "period_days": days,
            "product_trends": product_trends,
        }

    def update_recipe_costs(self, save_snapshots: bool = True) -> Dict:
        """Update all recipe costs using the recipe costing service"""

        try:
            result = self.recipe_costing_service.bulk_update_recipe_costs(
                Recipe.objects.filter(is_active=True), save_snapshot=save_snapshots
            )
            return result
        except Exception as e:
            logger.error(f"Error updating recipe costs: {e}")
            return {"updated": 0, "errors": 1}

    def get_cost_efficiency_analysis(self) -> Dict:
        """Get cost efficiency analysis for recipes"""

        try:
            efficient_recipes = (
                self.recipe_costing_service.get_recipes_by_cost_efficiency(limit=10)
            )
            return {
                "efficient_recipes": efficient_recipes,
                "analysis_date": timezone.now(),
            }
        except Exception as e:
            logger.error(f"Error getting cost efficiency analysis: {e}")
            return {"efficient_recipes": [], "error": str(e)}

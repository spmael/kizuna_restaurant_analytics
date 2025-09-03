import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple

from django.db.models import Avg, Count, Sum

from apps.analytics.models import DailySummary
from apps.restaurant_data.models import Sales

logger = logging.getLogger(__name__)


class RevenueAnalyticsService:
    """
    Comprehensive revenue analytics service for restaurant operations.

    Answers key revenue questions:
    - "How much money are we making?" → Total revenue trends
    - "What's driving our sales?" → Top categories/products
    - "When do we make the most money?" → Peak hours/days
    - "Are we growing?" → Growth rate comparisons
    - "Where's our opportunity?" → Underperforming areas
    """

    # Industry benchmarks for Cameroon restaurant market
    REVENUE_BENCHMARKS = {
        "daily_revenue_targets": {
            "small_restaurant": (50000, 150000),  # 50k-150k FCFA
            "medium_restaurant": (150000, 300000),  # 150k-300k FCFA
            "large_restaurant": (300000, 500000),  # 300k-500k FCFA
        },
        "growth_targets": {
            "monthly": (5, 15),  # 5-15% monthly growth
            "quarterly": (10, 25),  # 10-25% quarterly growth
        },
        "category_performance": {
            "main_dishes": (40, 60),  # 40-60% of revenue
            "beverages": (15, 25),  # 15-25% of revenue
            "appetizers": (10, 20),  # 10-20% of revenue
            "desserts": (5, 15),  # 5-15% of revenue
        },
        "payment_methods_cameroon": {
            "cash_percentage": (60, 80),  # 60-80% cash
            "mobile_money_percentage": (15, 30),  # 15-30% mobile money
            "card_percentage": (5, 15),  # 5-15% card
        },
    }

    def __init__(self):
        self.errors = []
        self.warnings = []

    def get_revenue_overview(self, start_date: date, end_date: date) -> Dict:
        """
        Get comprehensive revenue overview for a date range.
        Answers: "How much money are we making?"
        """
        try:
            # Get daily summaries for the period
            summaries = DailySummary.objects.filter(
                date__range=[start_date, end_date]
            ).order_by("date")

            if not summaries.exists():
                return {"error": "No data found for the specified period"}

            # Calculate key metrics
            total_revenue = summaries.aggregate(total=Sum("total_sales"))[
                "total"
            ] or Decimal("0")

            total_orders = summaries.aggregate(total=Sum("total_orders"))["total"] or 0

            total_customers = (
                summaries.aggregate(total=Sum("total_customers"))["total"] or 0
            )

            # Calculate averages
            days_count = summaries.count()
            avg_daily_revenue = (
                total_revenue / days_count if days_count > 0 else Decimal("0")
            )
            avg_daily_orders = total_orders / days_count if days_count > 0 else 0
            avg_daily_customers = total_customers / days_count if days_count > 0 else 0

            # Calculate growth metrics
            growth_metrics = self._calculate_revenue_growth(summaries)

            # Get revenue trends
            revenue_trends = self._get_revenue_trends(summaries)

            # Performance analysis
            performance_analysis = self._analyze_revenue_performance(
                avg_daily_revenue, total_revenue, days_count
            )

            return {
                "period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "days_count": days_count,
                },
                "total_metrics": {
                    "total_revenue": total_revenue,
                    "total_orders": total_orders,
                    "total_customers": total_customers,
                },
                "average_metrics": {
                    "avg_daily_revenue": avg_daily_revenue,
                    "avg_daily_orders": avg_daily_orders,
                    "avg_daily_customers": avg_daily_customers,
                    "avg_order_value": (
                        total_revenue / total_orders
                        if total_orders > 0
                        else Decimal("0")
                    ),
                    "avg_ticket_size": (
                        total_revenue / total_customers
                        if total_customers > 0
                        else Decimal("0")
                    ),
                },
                "growth_metrics": growth_metrics,
                "revenue_trends": revenue_trends,
                "performance_analysis": performance_analysis,
                "benchmark_comparison": self._compare_to_benchmarks(avg_daily_revenue),
            }

        except Exception as e:
            logger.error(f"Error getting revenue overview: {e}")
            return {"error": str(e)}

    def get_top_performing_categories(
        self, start_date: date, end_date: date, limit: int = 10
    ) -> Dict:
        """
        Get top performing product categories.
        Answers: "What's driving our sales?"
        """
        try:
            # Get sales data grouped by category
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

            # Calculate percentages
            total_revenue = sum(
                Decimal(str(item["total_revenue"])) for item in category_sales
            )

            categories = []
            for item in category_sales[:limit]:
                percentage = (
                    (
                        Decimal(str(item["total_revenue"]))
                        / total_revenue
                        * Decimal("100")
                    )
                    if total_revenue > 0
                    else Decimal("0")
                )

                # Convert avg_unit_price to Decimal
                avg_unit_price = item["avg_unit_price"]
                if avg_unit_price is not None:
                    avg_unit_price = Decimal(str(avg_unit_price))
                else:
                    avg_unit_price = Decimal("0")

                categories.append(
                    {
                        "category_name": item["product__sales_category__name"]
                        or "Uncategorized",
                        "total_revenue": item["total_revenue"],
                        "total_quantity": item["total_quantity"],
                        "order_count": item["order_count"],
                        "avg_unit_price": avg_unit_price,
                        "revenue_percentage": percentage,
                        "performance_grade": self._grade_category_performance(
                            percentage
                        ),
                    }
                )

            return {
                "period": f"{start_date} to {end_date}",
                "total_revenue": total_revenue,
                "categories": categories,
                "insights": self._generate_category_insights(categories),
            }

        except Exception as e:
            logger.error(f"Error getting top performing categories: {e}")
            return {"error": str(e)}

    def _get_product_cost(self, product_id: int, sale_date: date) -> Decimal:
        """
        Get actual product cost from ProductCostHistory.
        Falls back to estimated cost if no actual data available.

        Cost calculation priority:
        1. Actual cost from ProductCostHistory (most accurate)
        2. Average cost from historical data (good approximation)
        3. Industry standard 35% of selling price (fallback estimate)

        Note: 35% is more realistic than 30% for most restaurants, as it accounts for:
        - Ingredient costs
        - Preparation time
        - Overhead allocation
        - Market conditions in Cameroon
        """
        try:
            from apps.analytics.models import ProductCostHistory

            # Try to get the most recent cost data for this product
            cost_history = (
                ProductCostHistory.objects.filter(
                    product_id=product_id, purchase_date__lte=sale_date, is_active=True
                )
                .order_by("-purchase_date")
                .first()
            )

            if cost_history:
                return cost_history.unit_cost_in_recipe_units

            # Fallback: try to get average cost from all history
            avg_cost = ProductCostHistory.objects.filter(
                product_id=product_id, is_active=True
            ).aggregate(avg_cost=Avg("unit_cost_in_recipe_units"))["avg_cost"]

            if avg_cost:
                return avg_cost

        except Exception as e:
            logger.warning(f"Error getting product cost for product {product_id}: {e}")

        # Final fallback: use industry standard 35% (more realistic than 30%)
        return None  # Will be handled in the calling method

    def get_top_performing_products(
        self, start_date: date, end_date: date, limit: int = 20
    ) -> Dict:
        """
        Get top performing individual products.
        Answers: "What's driving our sales?" (product level)
        """
        try:
            # Get sales data grouped by product
            product_sales = (
                Sales.objects.filter(sale_date__range=[start_date, end_date])
                .values(
                    "product__id",  # Add product ID for cost lookup
                    "product__name",
                    "product__sales_category__name",
                    "product__current_selling_price",
                )
                .annotate(
                    total_revenue=Sum("total_sale_price"),
                    total_quantity=Sum("quantity_sold"),
                    order_count=Count("order_number", distinct=True),
                    avg_unit_price=Avg("unit_sale_price"),
                )
                .order_by("-total_revenue")
            )

            products = []
            for item in product_sales[:limit]:
                # Calculate profit margin using actual cost data
                current_price = (
                    item["product__current_selling_price"] or item["avg_unit_price"]
                )
                # Convert to Decimal for consistent calculations
                if current_price is not None:
                    current_price = Decimal(str(current_price))
                else:
                    current_price = Decimal("0")

                # Get actual product cost instead of assuming 30%
                product_cost = self._get_product_cost(
                    item["product__id"],
                    start_date,  # Use start_date as reference for cost lookup
                )

                if product_cost is not None:
                    # Use actual cost data
                    estimated_cost = product_cost
                    estimated_profit = current_price - estimated_cost
                    profit_margin = (
                        (estimated_profit / current_price * Decimal("100"))
                        if current_price > 0
                        else Decimal("0")
                    )
                else:
                    # Fallback to industry standard 35% (more realistic than 30%)
                    # 35% accounts for ingredient costs, preparation time, overhead, and Cameroon market conditions
                    estimated_cost = current_price * Decimal("0.35")
                    estimated_profit = current_price - estimated_cost
                    profit_margin = (
                        (estimated_profit / current_price * Decimal("100"))
                        if current_price > 0
                        else Decimal("0")
                    )

                # Convert avg_unit_price to Decimal as well
                avg_unit_price = item["avg_unit_price"]
                if avg_unit_price is not None:
                    avg_unit_price = Decimal(str(avg_unit_price))
                else:
                    avg_unit_price = Decimal("0")

                # Convert total_revenue to Decimal for consistent handling
                total_revenue = (
                    Decimal(str(item["total_revenue"]))
                    if item["total_revenue"] is not None
                    else Decimal("0")
                )

                products.append(
                    {
                        "product_name": item["product__name"],
                        "category": item["product__sales_category__name"]
                        or "Uncategorized",
                        "total_revenue": total_revenue,
                        "total_quantity": item["total_quantity"],
                        "order_count": item["order_count"],
                        "avg_unit_price": avg_unit_price,
                        "current_price": current_price,
                        "estimated_cost": estimated_cost,
                        "estimated_profit_margin": profit_margin,
                        "cost_data_source": (
                            "actual" if product_cost is not None else "estimated"
                        ),
                        "performance_grade": self._grade_product_performance(
                            total_revenue
                        ),
                    }
                )

            return {
                "period": f"{start_date} to {end_date}",
                "products": products,
                "insights": self._generate_product_insights(products),
            }

        except Exception as e:
            logger.error(f"Error getting top performing products: {e}")
            return {"error": str(e)}

    def get_time_based_analysis(self, start_date: date, end_date: date) -> Dict:
        """
        Get time-based revenue analysis.
        Answers: "When do we make the most money?"
        """
        try:
            # Get daily summaries for the period
            summaries = DailySummary.objects.filter(
                date__range=[start_date, end_date]
            ).order_by("date")

            if not summaries.exists():
                return {"error": "No data found for the specified period"}

            # Daily patterns
            daily_patterns = self._analyze_daily_patterns(summaries)

            # Weekly patterns
            weekly_patterns = self._analyze_weekly_patterns(summaries)

            # Peak hours analysis (if available)
            peak_hours = self._analyze_peak_hours(summaries)

            # Seasonal trends
            seasonal_trends = self._analyze_seasonal_trends(summaries)

            return {
                "period": f"{start_date} to {end_date}",
                "daily_patterns": daily_patterns,
                "weekly_patterns": weekly_patterns,
                "peak_hours": peak_hours,
                "seasonal_trends": seasonal_trends,
                "insights": self._generate_time_insights(
                    daily_patterns, weekly_patterns
                ),
            }

        except Exception as e:
            logger.error(f"Error getting time-based analysis: {e}")
            return {"error": str(e)}

    def get_growth_analysis(
        self, comparison_periods: List[Tuple[date, date]] = None
    ) -> Dict:
        """
        Get revenue growth analysis.
        Answers: "Are we growing?"
        """
        try:
            if not comparison_periods:
                # Default to last 3 months vs previous 3 months
                end_date = date.today() - timedelta(days=1)
                current_start = end_date - timedelta(days=90)
                previous_start = current_start - timedelta(days=90)
                comparison_periods = [
                    (current_start, end_date),
                    (previous_start, current_start - timedelta(days=1)),
                ]

            growth_data = []
            for i, (start_date, end_date) in enumerate(comparison_periods):
                period_data = self._calculate_period_metrics(start_date, end_date)
                period_data["period_name"] = f"Period {i+1}"
                period_data["start_date"] = start_date
                period_data["end_date"] = end_date
                growth_data.append(period_data)

            # Calculate growth rates
            if len(growth_data) >= 2:
                current = growth_data[0]
                previous = growth_data[1]

                growth_rates = self._calculate_growth_rates(current, previous)
            else:
                growth_rates = {}

            return {
                "comparison_periods": growth_data,
                "growth_rates": growth_rates,
                "growth_insights": self._generate_growth_insights(growth_rates),
            }

        except Exception as e:
            logger.error(f"Error getting growth analysis: {e}")
            return {"error": str(e)}

    def get_opportunity_analysis(self, start_date: date, end_date: date) -> Dict:
        """
        Get opportunity analysis for underperforming areas.
        Answers: "Where's our opportunity?"
        """
        try:
            # Get underperforming categories
            underperforming_categories = self._identify_underperforming_categories(
                start_date, end_date
            )

            # Get underperforming products
            underperforming_products = self._identify_underperforming_products(
                start_date, end_date
            )

            # Get low-margin products
            low_margin_products = self._identify_low_margin_products(
                start_date, end_date
            )

            # Get slow-moving inventory
            slow_moving_inventory = self._identify_slow_moving_inventory()

            # Get revenue optimization opportunities
            optimization_opportunities = self._identify_optimization_opportunities(
                start_date, end_date
            )

            return {
                "period": f"{start_date} to {end_date}",
                "underperforming_categories": underperforming_categories,
                "underperforming_products": underperforming_products,
                "low_margin_products": low_margin_products,
                "slow_moving_inventory": slow_moving_inventory,
                "optimization_opportunities": optimization_opportunities,
                "actionable_insights": self._generate_opportunity_insights(
                    underperforming_categories,
                    underperforming_products,
                    low_margin_products,
                ),
            }

        except Exception as e:
            logger.error(f"Error getting opportunity analysis: {e}")
            return {"error": str(e)}

    def get_payment_method_analysis(self, start_date: date, end_date: date) -> Dict:
        """
        Get payment method breakdown and analysis.
        """
        try:
            summaries = DailySummary.objects.filter(date__range=[start_date, end_date])

            if not summaries.exists():
                return {"error": "No data found for the specified period"}

            # Aggregate payment data
            payment_totals = summaries.aggregate(
                total_cash=Sum("cash_sales"),
                total_mobile_money=Sum("mobile_money_sales"),
                total_card=Sum("credit_card_sales"),
                total_other=Sum("other_payment_methods_sales"),
                total_sales=Sum("total_sales"),
            )

            total_sales = payment_totals["total_sales"] or Decimal("0")

            if total_sales > 0:
                payment_breakdown = {
                    "cash": {
                        "amount": payment_totals["total_cash"] or Decimal("0"),
                        "percentage": (
                            (
                                payment_totals["total_cash"]
                                / total_sales
                                * Decimal("100")
                            )
                            if payment_totals["total_cash"]
                            else Decimal("0")
                        ),
                    },
                    "mobile_money": {
                        "amount": payment_totals["total_mobile_money"] or Decimal("0"),
                        "percentage": (
                            (
                                payment_totals["total_mobile_money"]
                                / total_sales
                                * Decimal("100")
                            )
                            if payment_totals["total_mobile_money"]
                            else Decimal("0")
                        ),
                    },
                    "card": {
                        "amount": payment_totals["total_card"] or Decimal("0"),
                        "percentage": (
                            (
                                payment_totals["total_card"]
                                / total_sales
                                * Decimal("100")
                            )
                            if payment_totals["total_card"]
                            else Decimal("0")
                        ),
                    },
                    "other": {
                        "amount": payment_totals["total_other"] or Decimal("0"),
                        "percentage": (
                            (
                                payment_totals["total_other"]
                                / total_sales
                                * Decimal("100")
                            )
                            if payment_totals["total_other"]
                            else Decimal("0")
                        ),
                    },
                }
            else:
                payment_breakdown = {
                    "cash": {"amount": Decimal("0"), "percentage": 0},
                    "mobile_money": {"amount": Decimal("0"), "percentage": 0},
                    "card": {"amount": Decimal("0"), "percentage": 0},
                    "other": {"amount": Decimal("0"), "percentage": 0},
                }

            return {
                "period": f"{start_date} to {end_date}",
                "total_sales": total_sales,
                "payment_breakdown": payment_breakdown,
                "benchmark_comparison": self._compare_payment_methods_to_benchmarks(
                    payment_breakdown
                ),
                "insights": self._generate_payment_insights(payment_breakdown),
            }

        except Exception as e:
            logger.error(f"Error getting payment method analysis: {e}")
            return {"error": str(e)}

    def get_day_of_week_revenue(self, start_date: date, end_date: date) -> Dict:
        """
        Get revenue by day of the week in chart-ready format.
        Returns data specifically formatted for the day-of-week chart.
        """
        try:
            summaries = DailySummary.objects.filter(date__range=[start_date, end_date])

            if not summaries.exists():
                return {"error": "No data found for the specified period"}

            # Initialize day-of-week data structure
            day_revenue = {
                "Monday": [],
                "Tuesday": [],
                "Wednesday": [],
                "Thursday": [],
                "Friday": [],
                "Saturday": [],
                "Sunday": [],
            }

            # Collect revenue data for each day
            for summary in summaries:
                day_name = summary.date.strftime("%A")  # Gets full day name
                if day_name in day_revenue:
                    day_revenue[day_name].append(summary.total_sales or Decimal("0"))

            # Calculate average revenue for each day
            day_averages = {}
            for day, revenues in day_revenue.items():
                if revenues:
                    day_averages[day] = sum(revenues) / Decimal(str(len(revenues)))
                else:
                    day_averages[day] = Decimal("0")

            # Return in chart-ready format
            return {
                "labels": [
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                    "Sunday",
                ],
                "revenue": [
                    day_averages["Monday"],
                    day_averages["Tuesday"],
                    day_averages["Wednesday"],
                    day_averages["Thursday"],
                    day_averages["Friday"],
                    day_averages["Saturday"],
                    day_averages["Sunday"],
                ],
                "raw_data": day_averages,  # For debugging/insights
                "period": f"{start_date} to {end_date}",
            }

        except Exception as e:
            logger.error(f"Error getting day of week revenue: {e}")
            return {"error": str(e)}

    # === PRIVATE HELPER METHODS ===

    def _calculate_revenue_growth(self, summaries) -> Dict:
        """Calculate revenue growth metrics for any period"""
        if summaries.count() < 2:
            return {}

        # Get first and last period for comparison (period length depends on data available)
        total_days = summaries.count()
        if total_days < 14:  # If less than 2 weeks, compare first half vs second half
            mid_point = total_days // 2
            first_period = summaries[:mid_point]
            last_period = summaries.order_by("-date")[:mid_point]
        else:  # If 2+ weeks, compare first week vs last week
            first_period = summaries[:7]
            last_period = summaries.order_by("-date")[:7]

        if first_period.count() < 1 or last_period.count() < 1:
            return {}

        first_period_revenue = first_period.aggregate(total=Sum("total_sales"))[
            "total"
        ] or Decimal("0")
        last_period_revenue = last_period.aggregate(total=Sum("total_sales"))[
            "total"
        ] or Decimal("0")

        if first_period_revenue > 0:
            growth_rate = (
                (last_period_revenue - first_period_revenue) / first_period_revenue
            ) * Decimal("100")
        else:
            growth_rate = Decimal("0")

        return {
            "period_over_period_growth": growth_rate,
            "growth_trend": (
                "increasing"
                if growth_rate > 0
                else "decreasing" if growth_rate < 0 else "stable"
            ),
        }

    def _get_revenue_trends(self, summaries) -> Dict:
        """Get revenue trends over time"""
        daily_data = []
        for summary in summaries:
            daily_data.append(
                {
                    "date": summary.date,
                    "revenue": summary.total_sales,
                    "orders": summary.total_orders,
                    "customers": summary.total_customers,
                }
            )

        return {
            "daily_data": daily_data,
            "trend_direction": self._determine_trend_direction(daily_data),
        }

    def _analyze_revenue_performance(
        self, avg_daily_revenue: Decimal, total_revenue: Decimal, days_count: int
    ) -> Dict:
        """Analyze revenue performance against benchmarks"""
        # Determine restaurant size based on daily revenue
        if avg_daily_revenue < Decimal("150000"):
            size_category = "small_restaurant"
        elif avg_daily_revenue < Decimal("300000"):
            size_category = "medium_restaurant"
        else:
            size_category = "large_restaurant"

        benchmarks = self.REVENUE_BENCHMARKS["daily_revenue_targets"][size_category]
        benchmark_min = Decimal(str(benchmarks[0]))
        benchmark_max = Decimal(str(benchmarks[1]))

        performance_score = Decimal("0")
        if benchmark_min <= avg_daily_revenue <= benchmark_max:
            performance_score = Decimal("100")
        elif avg_daily_revenue > benchmark_max:
            performance_score = Decimal("120")  # Exceeding expectations
        else:
            performance_score = (avg_daily_revenue / benchmark_min) * Decimal("100")

        return {
            "size_category": size_category,
            "target_range": (benchmark_min, benchmark_max),
            "performance_score": performance_score,
            "performance_grade": self._grade_performance(performance_score),
        }

    def _compare_to_benchmarks(self, avg_daily_revenue: Decimal) -> Dict:
        """Compare revenue to industry benchmarks"""
        comparisons = {}

        for size, (min_target, max_target) in self.REVENUE_BENCHMARKS[
            "daily_revenue_targets"
        ].items():
            min_target_decimal = Decimal(str(min_target))
            max_target_decimal = Decimal(str(max_target))
            if min_target_decimal <= avg_daily_revenue <= max_target_decimal:
                comparisons[size] = "within_range"
            elif avg_daily_revenue > max_target_decimal:
                comparisons[size] = "above_range"
            else:
                comparisons[size] = "below_range"

        return comparisons

    def _grade_category_performance(self, revenue_percentage: Decimal) -> str:
        """Grade category performance based on revenue percentage"""
        if revenue_percentage >= Decimal("20"):
            return "A"
        elif revenue_percentage >= Decimal("15"):
            return "B"
        elif revenue_percentage >= Decimal("10"):
            return "C"
        elif revenue_percentage >= Decimal("5"):
            return "D"
        else:
            return "F"

    def _grade_product_performance(self, total_revenue: Decimal) -> str:
        """Grade product performance based on total revenue"""
        if total_revenue >= Decimal("100000"):
            return "A"
        elif total_revenue >= Decimal("50000"):
            return "B"
        elif total_revenue >= Decimal("25000"):
            return "C"
        elif total_revenue >= Decimal("10000"):
            return "D"
        else:
            return "F"

    def _grade_performance(self, score: Decimal) -> str:
        """Grade overall performance"""
        if score >= Decimal("100"):
            return "A"
        elif score >= Decimal("80"):
            return "B"
        elif score >= Decimal("60"):
            return "C"
        elif score >= Decimal("40"):
            return "D"
        else:
            return "F"

    def _analyze_daily_patterns(self, summaries) -> Dict:
        """Analyze daily revenue patterns"""
        daily_averages = {}
        for summary in summaries:
            day_name = summary.date.strftime("%A")
            if day_name not in daily_averages:
                daily_averages[day_name] = []
            daily_averages[day_name].append(summary.total_sales)

        # Calculate averages
        for day in daily_averages:
            daily_averages[day] = sum(daily_averages[day]) / Decimal(
                str(len(daily_averages[day]))
            )

        # Find best and worst days
        best_day = max(daily_averages.items(), key=lambda x: x[1])
        worst_day = min(daily_averages.items(), key=lambda x: x[1])

        return {
            "daily_averages": daily_averages,
            "best_day": {"day": best_day[0], "revenue": best_day[1]},
            "worst_day": {"day": worst_day[0], "revenue": worst_day[1]},
        }

    def _analyze_weekly_patterns(self, summaries) -> Dict:
        """Analyze weekly revenue patterns"""
        weekly_data = {}
        for summary in summaries:
            week_start = summary.date - timedelta(days=summary.date.weekday())
            week_key = week_start.strftime("%Y-%m-%d")

            if week_key not in weekly_data:
                weekly_data[week_key] = {
                    "week_start": week_start,
                    "total_revenue": Decimal("0"),
                    "total_orders": 0,
                    "total_customers": 0,
                }

            weekly_data[week_key]["total_revenue"] += summary.total_sales
            weekly_data[week_key]["total_orders"] += summary.total_orders
            weekly_data[week_key]["total_customers"] += summary.total_customers

        return {
            "weekly_data": list(weekly_data.values()),
            "avg_weekly_revenue": (
                sum(w["total_revenue"] for w in weekly_data.values())
                / Decimal(str(len(weekly_data)))
                if weekly_data
                else Decimal("0")
            ),
        }

    def _analyze_peak_hours(self, summaries) -> Dict:
        """Analyze peak hours (placeholder for future implementation)"""
        # This would require time-based sales data
        return {
            "note": "Peak hours analysis requires time-based sales data",
            "estimated_peak_hours": ["12:00-14:00", "19:00-21:00"],
        }

    def _analyze_seasonal_trends(self, summaries) -> Dict:
        """Analyze seasonal trends"""
        monthly_data = {}
        for summary in summaries:
            month_key = summary.date.strftime("%Y-%m")
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    "month": month_key,
                    "total_revenue": Decimal("0"),
                    "days_count": 0,
                }

            monthly_data[month_key]["total_revenue"] += summary.total_sales
            monthly_data[month_key]["days_count"] += 1

        # Calculate monthly averages
        for month in monthly_data:
            monthly_data[month]["avg_daily_revenue"] = monthly_data[month][
                "total_revenue"
            ] / Decimal(str(monthly_data[month]["days_count"]))

        return {
            "monthly_data": list(monthly_data.values()),
        }

    def _calculate_period_metrics(self, start_date: date, end_date: date) -> Dict:
        """Calculate metrics for a specific period"""
        summaries = DailySummary.objects.filter(date__range=[start_date, end_date])

        if not summaries.exists():
            return {}

        total_revenue = summaries.aggregate(total=Sum("total_sales"))[
            "total"
        ] or Decimal("0")
        total_orders = summaries.aggregate(total=Sum("total_orders"))["total"] or 0
        total_customers = (
            summaries.aggregate(total=Sum("total_customers"))["total"] or 0
        )
        days_count = summaries.count()

        return {
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "total_customers": total_customers,
            "avg_daily_revenue": (
                total_revenue / Decimal(str(days_count))
                if days_count > 0
                else Decimal("0")
            ),
            "avg_order_value": (
                total_revenue / Decimal(str(total_orders))
                if total_orders > 0
                else Decimal("0")
            ),
            "avg_ticket_size": (
                total_revenue / Decimal(str(total_customers))
                if total_customers > 0
                else Decimal("0")
            ),
        }

    def _calculate_growth_rates(self, current: Dict, previous: Dict) -> Dict:
        """Calculate growth rates between two periods"""
        growth_rates = {}

        for metric in [
            "total_revenue",
            "total_orders",
            "total_customers",
            "avg_daily_revenue",
        ]:
            current_val = current.get(metric, 0)
            previous_val = previous.get(metric, 0)

            if previous_val > 0:
                growth_rate = ((current_val - previous_val) / previous_val) * Decimal(
                    "100"
                )
            else:
                growth_rate = Decimal("0")

            growth_rates[f"{metric}_growth"] = growth_rate

        return growth_rates

    def _identify_underperforming_categories(
        self, start_date: date, end_date: date
    ) -> List[Dict]:
        """Identify underperforming product categories"""
        category_sales = (
            Sales.objects.filter(sale_date__range=[start_date, end_date])
            .values("product__sales_category__name")
            .annotate(
                total_revenue=Sum("total_sale_price"),
                total_quantity=Sum("quantity_sold"),
            )
            .order_by("total_revenue")
        )

        total_revenue = sum(item["total_revenue"] for item in category_sales)

        underperforming = []
        for item in category_sales:
            percentage = (
                (
                    Decimal(str(item["total_revenue"]))
                    / Decimal(str(total_revenue))
                    * Decimal("100")
                )
                if total_revenue > 0
                else Decimal("0")
            )
            if percentage < 5:  # Less than 5% of total revenue
                underperforming.append(
                    {
                        "category": item["product__sales_category__name"]
                        or "Uncategorized",
                        "revenue": item["total_revenue"],
                        "percentage": percentage,
                        "suggestion": "Consider menu optimization or marketing focus",
                    }
                )

        return underperforming

    def _identify_underperforming_products(
        self, start_date: date, end_date: date
    ) -> List[Dict]:
        """Identify underperforming products"""
        product_sales = (
            Sales.objects.filter(sale_date__range=[start_date, end_date])
            .values(
                "product__name",
                "product__sales_category__name",
            )
            .annotate(
                total_revenue=Sum("total_sale_price"),
                total_quantity=Sum("quantity_sold"),
            )
            .order_by("total_revenue")
        )

        underperforming = []
        for item in product_sales:
            if item["total_revenue"] < 10000:  # Less than 10k FCFA
                underperforming.append(
                    {
                        "product": item["product__name"],
                        "category": item["product__sales_category__name"]
                        or "Uncategorized",
                        "revenue": item["total_revenue"],
                        "quantity": item["total_quantity"],
                        "suggestion": "Review pricing, positioning, or consider removal",
                    }
                )

        return underperforming

    def _identify_low_margin_products(
        self, start_date: date, end_date: date
    ) -> List[Dict]:
        """Identify low margin products"""
        # This would require cost data - simplified version
        return []

    def _identify_slow_moving_inventory(self) -> List[Dict]:
        """Identify slow moving inventory"""
        # This would require inventory data - simplified version
        return []

    def _identify_optimization_opportunities(
        self, start_date: date, end_date: date
    ) -> List[Dict]:
        """Identify revenue optimization opportunities"""
        opportunities = []

        # Analyze average order value
        summaries = DailySummary.objects.filter(date__range=[start_date, end_date])

        if summaries.exists():
            avg_aov = summaries.aggregate(avg=Avg("average_order_value"))[
                "avg"
            ] or Decimal("0")
            if avg_aov < Decimal("5000"):  # Less than 5k FCFA average order
                opportunities.append(
                    {
                        "type": "low_average_order_value",
                        "current_value": avg_aov,
                        "target_value": 5000,
                        "suggestion": "Implement upselling strategies and combo offers",
                    }
                )

        return opportunities

    def _determine_trend_direction(self, daily_data: List[Dict]) -> str:
        """Determine overall trend direction"""
        if len(daily_data) < 2:
            return "insufficient_data"

        # Simple trend analysis
        first_half = daily_data[: len(daily_data) // 2]
        second_half = daily_data[len(daily_data) // 2 :]

        first_avg = (
            sum(d["revenue"] for d in first_half) / Decimal(str(len(first_half)))
            if first_half
            else Decimal("0")
        )
        second_avg = (
            sum(d["revenue"] for d in second_half) / Decimal(str(len(second_half)))
            if second_half
            else Decimal("0")
        )

        if second_avg > first_avg * Decimal("1.05"):
            return "increasing"
        elif second_avg < first_avg * Decimal("0.95"):
            return "decreasing"
        else:
            return "stable"

    def _compare_payment_methods_to_benchmarks(self, payment_breakdown: Dict) -> Dict:
        """Compare payment methods to Cameroon benchmarks"""
        benchmarks = self.REVENUE_BENCHMARKS["payment_methods_cameroon"]
        comparison = {}

        for method, data in payment_breakdown.items():
            if method == "cash":
                benchmark_range = benchmarks["cash_percentage"]
            elif method == "mobile_money":
                benchmark_range = benchmarks["mobile_money_percentage"]
            elif method == "card":
                benchmark_range = benchmarks["card_percentage"]
            else:
                continue

            percentage = data["percentage"]
            if benchmark_range[0] <= percentage <= benchmark_range[1]:
                comparison[method] = "within_benchmark"
            elif percentage > benchmark_range[1]:
                comparison[method] = "above_benchmark"
            else:
                comparison[method] = "below_benchmark"

        return comparison

    # === INSIGHT GENERATION METHODS ===

    def _generate_category_insights(self, categories: List[Dict]) -> List[str]:
        """Generate insights from category performance"""
        insights = []

        if not categories:
            return insights

        top_category = categories[0]
        if top_category["revenue_percentage"] > 40:
            insights.append(
                f"Strong category concentration: {top_category['category_name']} drives {top_category['revenue_percentage']:.1f}% of revenue"
            )

        low_performing = [c for c in categories if c["performance_grade"] in ["D", "F"]]
        if low_performing:
            insights.append(
                f"{len(low_performing)} categories are underperforming and may need attention"
            )

        return insights

    def _generate_product_insights(self, products: List[Dict]) -> List[str]:
        """Generate insights from product performance"""
        insights = []

        if not products:
            return insights

        top_product = products[0]
        insights.append(
            f"Top performer: {top_product['product_name']} generated {top_product['total_revenue']} FCFA"
        )

        high_margin = [p for p in products if p["estimated_profit_margin"] > 60]
        if high_margin:
            insights.append(
                f"{len(high_margin)} products have high profit margins (>60%)"
            )

        return insights

    def _generate_time_insights(
        self, daily_patterns: Dict, weekly_patterns: Dict
    ) -> List[str]:
        """Generate insights from time-based analysis"""
        insights = []

        if daily_patterns:
            best_day = daily_patterns.get("best_day", {})
            worst_day = daily_patterns.get("worst_day", {})

            if best_day and worst_day:
                insights.append(
                    f"Best performing day: {best_day['day']} ({best_day['revenue']:.0f} FCFA)"
                )
                insights.append(
                    f"Lowest performing day: {worst_day['day']} ({worst_day['revenue']:.0f} FCFA)"
                )

        return insights

    def _generate_growth_insights(self, growth_rates: Dict) -> List[str]:
        """Generate insights from growth analysis"""
        insights = []

        revenue_growth = growth_rates.get("total_revenue_growth", 0)
        if revenue_growth > 10:
            insights.append(f"Strong revenue growth: {revenue_growth:.1f}% increase")
        elif revenue_growth < -10:
            insights.append(
                f"Revenue declining: {revenue_growth:.1f}% decrease - needs attention"
            )
        elif revenue_growth > 0:
            insights.append(f"Moderate growth: {revenue_growth:.1f}% increase")
        else:
            insights.append("Revenue is stable")

        return insights

    def _generate_opportunity_insights(
        self,
        underperforming_categories: List,
        underperforming_products: List,
        low_margin_products: List,
    ) -> List[str]:
        """Generate insights from opportunity analysis"""
        insights = []

        if underperforming_categories:
            insights.append(
                f"{len(underperforming_categories)} categories are underperforming"
            )

        if underperforming_products:
            insights.append(f"{len(underperforming_products)} products need attention")

        if low_margin_products:
            insights.append(
                f"{len(low_margin_products)} products have low profit margins"
            )

        if not insights:
            insights.append("All areas performing well within expectations")

        return insights

    def get_revenue_insights(self, start_date: date, end_date: date) -> Dict:
        """
        Get comprehensive revenue insights and recommendations.
        Returns insights from all analyses combined.
        """
        try:
            # Get all analyses
            revenue_overview = self.get_revenue_overview(start_date, end_date)
            top_categories = self.get_top_performing_categories(start_date, end_date)
            top_products = self.get_top_performing_products(start_date, end_date)
            time_analysis = self.get_time_based_analysis(start_date, end_date)
            growth_analysis = self.get_growth_analysis()
            opportunity_analysis = self.get_opportunity_analysis(start_date, end_date)
            payment_analysis = self.get_payment_method_analysis(start_date, end_date)

            # Generate comprehensive insights
            insights = {
                "revenue_performance": [],
                "category_insights": [],
                "product_insights": [],
                "time_insights": [],
                "growth_insights": [],
                "opportunity_insights": [],
                "payment_insights": [],
                "recommendations": [],
            }

            # Revenue performance insights
            if "error" not in revenue_overview:
                overview = revenue_overview
                avg_daily_revenue = overview.get("average_metrics", {}).get(
                    "avg_daily_revenue", 0
                )

                if avg_daily_revenue < 100000:
                    insights["revenue_performance"].append(
                        "Daily revenue is below target. Consider promotional activities."
                    )
                elif avg_daily_revenue > 300000:
                    insights["revenue_performance"].append(
                        "Excellent daily revenue performance!"
                    )

                performance = overview.get("performance_analysis", {})
                if performance.get("performance_grade") == "A":
                    insights["revenue_performance"].append(
                        "Outstanding performance! Keep up the excellent work."
                    )
                elif performance.get("performance_grade") in ["D", "F"]:
                    insights["revenue_performance"].append(
                        "Performance needs improvement. Review operations and pricing."
                    )

            # Category insights
            if "error" not in top_categories:
                categories = top_categories.get("categories", [])
                if categories:
                    top_category = categories[0]
                    if top_category["revenue_percentage"] > 50:
                        insights["category_insights"].append(
                            f"High concentration in {top_category['category_name']} ({top_category['revenue_percentage']:.1f}%). "
                            "Consider diversifying menu to reduce risk."
                        )

                    low_performing = [
                        c for c in categories if c["performance_grade"] in ["D", "F"]
                    ]
                    if low_performing:
                        insights["category_insights"].append(
                            f"{len(low_performing)} categories are underperforming. "
                            "Review menu strategy and marketing focus."
                        )

            # Product insights
            if "error" not in top_products:
                products = top_products.get("products", [])
                if products:
                    top_product = products[0]
                    insights["product_insights"].append(
                        f"Top performer: {top_product['product_name']} generated {top_product['total_revenue']} FCFA"
                    )

                    high_margin = [
                        p for p in products if p["estimated_profit_margin"] > 60
                    ]
                    if high_margin:
                        insights["product_insights"].append(
                            f"{len(high_margin)} products have excellent profit margins (>60%). "
                            "Consider promoting these items."
                        )

            # Time insights
            if "error" not in time_analysis:
                daily_patterns = time_analysis.get("daily_patterns", {})
                if daily_patterns:
                    best_day = daily_patterns.get("best_day", {})
                    worst_day = daily_patterns.get("worst_day", {})

                    if best_day and worst_day:
                        day_variance = best_day.get("revenue", 0) - worst_day.get(
                            "revenue", 0
                        )
                        if day_variance > 50000:
                            insights["time_insights"].append(
                                f"High day-to-day variance ({day_variance:.0f} FCFA). "
                                f"Best: {best_day['day']}, Worst: {worst_day['day']}. "
                                "Consider strategies to boost slow days."
                            )

            # Growth insights
            if "error" not in growth_analysis:
                growth_rates = growth_analysis.get("growth_rates", {})
                revenue_growth = growth_rates.get("total_revenue_growth", 0)

                if revenue_growth > 15:
                    insights["growth_insights"].append(
                        "Excellent growth rate! Business is expanding well."
                    )
                elif revenue_growth < -10:
                    insights["growth_insights"].append(
                        "Revenue declining. Immediate action needed to reverse trend."
                    )
                elif revenue_growth > 0:
                    insights["growth_insights"].append(
                        "Moderate growth. Consider strategies to accelerate."
                    )
                else:
                    insights["growth_insights"].append(
                        "Revenue is stable. Look for growth opportunities."
                    )

            # Opportunity insights
            if "error" not in opportunity_analysis:
                opportunities = opportunity_analysis.get("actionable_insights", [])
                insights["opportunity_insights"].extend(opportunities)

            # Payment insights
            if "error" not in payment_analysis:
                payment_breakdown = payment_analysis.get("payment_breakdown", {})
                cash_pct = payment_breakdown.get("cash", {}).get("percentage", 0)
                mobile_pct = payment_breakdown.get("mobile_money", {}).get(
                    "percentage", 0
                )

                if cash_pct > 80:
                    insights["payment_insights"].append(
                        "High cash dependency. Consider promoting digital payment methods for better tracking."
                    )
                elif mobile_pct > 30:
                    insights["payment_insights"].append(
                        "Strong mobile money adoption. Good for digital transformation and customer convenience."
                    )

            # Generate recommendations
            insights["recommendations"] = self._generate_recommendations(insights)

            return {
                "period": f"{start_date} to {end_date}",
                "insights": insights,
            }

        except Exception as e:
            logger.error(f"Error getting revenue insights: {e}")
            return {"error": str(e)}

    def _generate_recommendations(self, insights: Dict) -> List[Dict]:
        """Generate actionable recommendations based on insights"""
        recommendations = []

        # Revenue performance recommendations
        if any(
            "below target" in insight for insight in insights["revenue_performance"]
        ):
            recommendations.append(
                {
                    "category": "Revenue Growth",
                    "priority": "High",
                    "action": "Implement promotional campaigns and review pricing strategy",
                    "impact": "Increase daily revenue by 15-25%",
                }
            )

        # Category recommendations
        if any(
            "high concentration" in insight for insight in insights["category_insights"]
        ):
            recommendations.append(
                {
                    "category": "Menu Diversification",
                    "priority": "Medium",
                    "action": "Develop new menu items in underperforming categories",
                    "impact": "Reduce risk and increase customer satisfaction",
                }
            )

        # Product recommendations
        if any(
            "high profit margins" in insight for insight in insights["product_insights"]
        ):
            recommendations.append(
                {
                    "category": "Product Promotion",
                    "priority": "Medium",
                    "action": "Feature high-margin items prominently in menu and marketing",
                    "impact": "Increase overall profitability",
                }
            )

        # Time-based recommendations
        if any(
            "high day-to-day variance" in insight
            for insight in insights["time_insights"]
        ):
            recommendations.append(
                {
                    "category": "Operations Optimization",
                    "priority": "Medium",
                    "action": "Implement special promotions for slow days and optimize staffing",
                    "impact": "Smooth out daily revenue fluctuations",
                }
            )

        # Growth recommendations
        if any("declining" in insight for insight in insights["growth_insights"]):
            recommendations.append(
                {
                    "category": "Business Recovery",
                    "priority": "High",
                    "action": "Conduct customer feedback survey and review competitive positioning",
                    "impact": "Identify and address root causes of decline",
                }
            )

        # Payment recommendations
        if any(
            "high cash dependency" in insight
            for insight in insights["payment_insights"]
        ):
            recommendations.append(
                {
                    "category": "Digital Transformation",
                    "priority": "Low",
                    "action": "Promote mobile money and card payments with incentives",
                    "impact": "Improve transaction tracking and customer convenience",
                }
            )

        return recommendations

    def _generate_payment_insights(self, payment_breakdown: Dict) -> List[str]:
        """Generate insights from payment method analysis"""
        insights = []

        cash_pct = payment_breakdown.get("cash", {}).get("percentage", 0)
        mobile_pct = payment_breakdown.get("mobile_money", {}).get("percentage", 0)

        if cash_pct > 80:
            insights.append(
                "High cash dependency - consider promoting digital payments"
            )
        elif mobile_pct > 30:
            insights.append(
                "Strong mobile money adoption - good for digital transformation"
            )

        return insights

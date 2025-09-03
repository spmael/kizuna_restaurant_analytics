import json
import logging
from datetime import date, timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Avg, Sum

from apps.analytics.models import DailySummary
from apps.recipes.models import Recipe

from .cost_analytics import CostAnalyticsService
from .revenue_analytics import RevenueAnalyticsService
from .services import DailyAnalyticsService

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal objects"""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)  # Convert Decimal to float for JSON serialization
        return super().default(obj)


class DashboardService:
    """Service for handling dashboard data and analytics"""

    def __init__(self):
        self.revenue_service = RevenueAnalyticsService()
        self.cost_service = CostAnalyticsService()
        self.daily_service = DailyAnalyticsService()

    def get_dashboard_data(self, selected_days=7):
        """Get comprehensive dashboard data for the unified dashboard"""
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=selected_days - 1)

        try:
            # Get daily summaries for the period
            recent_summaries = DailySummary.objects.filter(
                date__range=[start_date, end_date]
            ).order_by("date")

            # Calculate week totals (period totals)
            week_totals = recent_summaries.aggregate(
                total_sales=Sum("total_sales"),
                total_orders=Sum("total_orders"),
                total_customers=Sum("total_customers"),
                registered_customers=Sum("registered_customers"),
                walk_in_customers=Sum("walk_in_customers"),
                avg_food_cost_pct=Avg("food_cost_percentage"),
                avg_order_value=Avg("average_order_value"),
            )

            # Calculate change percentages (comparing to previous period)
            previous_start = start_date - timedelta(days=selected_days)
            previous_end = start_date - timedelta(days=1)
            previous_summaries = DailySummary.objects.filter(
                date__range=[previous_start, previous_end]
            )

            previous_totals = previous_summaries.aggregate(
                total_sales=Sum("total_sales"),
                total_orders=Sum("total_orders"),
                total_customers=Sum("total_customers"),
            )

            # Calculate percentage changes
            sales_change = 0
            orders_change = 0
            customers_change = 0

            if previous_totals["total_sales"] and previous_totals["total_sales"] > 0:
                current_sales = week_totals["total_sales"] or Decimal("0")
                previous_sales = previous_totals["total_sales"]
                sales_change = (
                    (current_sales - previous_sales) / previous_sales
                ) * Decimal("100")

            if previous_totals["total_orders"] and previous_totals["total_orders"] > 0:
                current_orders = week_totals["total_orders"] or 0
                previous_orders = previous_totals["total_orders"]
                orders_change = (
                    (current_orders - previous_orders) / previous_orders
                ) * Decimal("100")

            if (
                previous_totals["total_customers"]
                and previous_totals["total_customers"] > 0
            ):
                current_customers = week_totals["total_customers"] or 0
                previous_customers = previous_totals["total_customers"]
                customers_change = (
                    (current_customers - previous_customers) / previous_customers
                ) * Decimal("100")

            # Get comprehensive revenue analytics data
            revenue_analytics = self.get_revenue_analytics_data(start_date, end_date)

            # Get revenue insights
            revenue_insights = self.get_revenue_insights_data(start_date, end_date)

            # Get top products
            top_products = self.revenue_service.get_top_performing_products(
                start_date, end_date, limit=5
            )

            # Get category data from revenue service (single source of truth for both sections)
            top_categories = self.revenue_service.get_top_performing_categories(
                start_date, end_date
            )
            categories_data = top_categories.get("categories", [])

            # Use the same data for both Chapter 1 and Chapter 2
            category_sales = categories_data  # For backward compatibility

            # Prepare revenue trends data
            revenue_trends = []
            max_sales = Decimal("0")
            if recent_summaries:
                max_sales = max(
                    summary.total_sales or Decimal("0") for summary in recent_summaries
                )

            for summary in recent_summaries:
                sales = summary.total_sales or Decimal("0")
                percentage = (
                    (sales / max_sales * Decimal("100"))
                    if max_sales > 0
                    else Decimal("0")
                )
                revenue_trends.append(
                    {
                        "date": summary.date,
                        "sales": sales,
                        "percentage": percentage,
                        "orders": summary.total_orders or 0,
                        "customers": summary.total_customers or 0,
                    }
                )

            # Get recipe statistics
            recipe_stats = self.get_recipe_stats()

            # Get recipes with costs
            recipes_with_costs = self.get_recipes_with_costs()

            # Get yesterday's data for insights
            yesterday = DailySummary.objects.filter(date=end_date).first()

            # Prepare chart data
            revenue_json = {
                "revenue": [
                    summary.total_sales or Decimal("0") for summary in recent_summaries
                ],
                "labels": [
                    summary.date.strftime("%d/%m") for summary in recent_summaries
                ],
            }

            category_json = {
                "revenue": [
                    cat.get("total_revenue", Decimal("0")) for cat in category_sales
                ],
                "labels": [
                    cat.get("category_name", "Unknown") for cat in category_sales
                ],
            }

            # Combine all data
            dashboard_data = {
                "week_totals": week_totals,
                "sales_change": sales_change,
                "orders_change": orders_change,
                "customers_change": customers_change,
                "top_products": top_products,
                "category_sales": category_sales,
                "revenue_trends": revenue_trends,
                "recipe_stats": recipe_stats,
                "recipes_with_costs": recipes_with_costs,
                "yesterday": yesterday,
                "revenue_json": json.dumps(revenue_json, cls=DecimalEncoder),
                "category_json": json.dumps(category_json, cls=DecimalEncoder),
                "selected_days": selected_days,
                "date_range": {
                    "start": start_date,
                    "end": end_date,
                },
                "recent_summaries": recent_summaries,
            }

            # Add revenue analytics data if available
            if "error" not in revenue_analytics:
                dashboard_data.update(
                    {
                        "revenue_overview": revenue_analytics.get(
                            "revenue_overview", {}
                        ),
                        "top_categories": revenue_analytics.get("top_categories", {}),
                        "time_analysis": revenue_analytics.get("time_analysis", {}),
                        "growth_analysis": revenue_analytics.get("growth_analysis", {}),
                        "opportunity_analysis": revenue_analytics.get(
                            "opportunity_analysis", {}
                        ),
                        "payment_analysis": revenue_analytics.get(
                            "payment_analysis", {}
                        ),
                    }
                )

                # Add chart data for revenue section using existing revenue service instance
                # Get day-of-week revenue data using the new dedicated function
                day_of_week_data = self.revenue_service.get_day_of_week_revenue(
                    start_date, end_date
                )

                # Get payment method analysis
                payment_analysis = self.revenue_service.get_payment_method_analysis(
                    start_date, end_date
                )
                payment_breakdown = payment_analysis.get("payment_breakdown", {})

                # Get top performing products
                top_products = self.revenue_service.get_top_performing_products(
                    start_date, end_date, limit=5
                )
                products_data = top_products.get("products", [])

                # Use the same category data for revenue section (already fetched above)
                revenue_category_data = {
                    "revenue": [
                        cat.get("total_revenue", Decimal("0")) for cat in category_sales
                    ],
                    "labels": [
                        cat.get("category_name", "Unknown") for cat in category_sales
                    ],
                }

                # Import and use utility functions for proper chart data preparation
                from apps.analytics.utils.revenue_utils import RevenueChartUtils

                chart_utils = RevenueChartUtils()

                # Get properly formatted daily revenue chart data
                daily_revenue_chart_data = chart_utils.prepare_daily_revenue_chart_data(
                    start_date, end_date
                )

                # Get properly formatted payment method chart data
                payment_chart_data = chart_utils.prepare_payment_method_chart_data(
                    start_date, end_date
                )

                dashboard_data.update(
                    {
                        "daily_revenue_chart": json.dumps(
                            {
                                "labels": (
                                    daily_revenue_chart_data.get("data", {}).get(
                                        "labels", []
                                    )
                                    if not daily_revenue_chart_data.get("error")
                                    else []
                                ),
                                "revenue": (
                                    daily_revenue_chart_data.get("data", {})
                                    .get("datasets", [{}])[0]
                                    .get("data", [])
                                    if daily_revenue_chart_data.get("data", {}).get(
                                        "datasets"
                                    )
                                    and not daily_revenue_chart_data.get("error")
                                    else []
                                ),
                            },
                            cls=DecimalEncoder,
                        ),
                        "revenue_category_chart": json.dumps(
                            revenue_category_data, cls=DecimalEncoder
                        ),
                        "time_based_chart": json.dumps(
                            {
                                "labels": day_of_week_data.get(
                                    "labels",
                                    [
                                        "Monday",
                                        "Tuesday",
                                        "Wednesday",
                                        "Thursday",
                                        "Friday",
                                        "Saturday",
                                        "Sunday",
                                    ],
                                ),
                                "revenue": day_of_week_data.get(
                                    "revenue", [0, 0, 0, 0, 0, 0, 0]
                                ),
                            },
                            cls=DecimalEncoder,
                        ),
                        "payment_chart": json.dumps(
                            {
                                "labels": (
                                    ["Cash", "Mobile Money", "Card", "Other"]
                                    if not payment_chart_data.get("error")
                                    else []
                                ),
                                "amounts": (
                                    payment_chart_data.get("data", {})
                                    .get("datasets", [{}])[0]
                                    .get("data", [])
                                    if payment_chart_data.get("data", {}).get(
                                        "datasets"
                                    )
                                    and not payment_chart_data.get("error")
                                    else []
                                ),
                            },
                            cls=DecimalEncoder,
                        ),
                        "product_chart": json.dumps(
                            {
                                "labels": [
                                    product.get("product_name", "Unknown")
                                    for product in products_data
                                ],
                                "revenue": [
                                    product.get("total_revenue", Decimal("0"))
                                    for product in products_data
                                ],
                            },
                            cls=DecimalEncoder,
                        ),
                    }
                )

            # Add revenue insights data if available
            if "error" not in revenue_insights:
                dashboard_data["insights"] = revenue_insights.get("insights", {})

            # Get cost analytics data for Chapter 3: Cost Chronicles
            cost_analytics_data = self.get_cost_analytics_data(start_date, end_date)

            # Add cost analytics data if available
            if "error" not in cost_analytics_data.get("cost_analytics", {}):
                dashboard_data.update(
                    {
                        "cost_analytics": cost_analytics_data.get("cost_analytics", {}),
                        "cost_metrics": cost_analytics_data.get("cost_metrics", {}),
                    }
                )
            else:
                dashboard_data.update(
                    {
                        "cost_analytics": {
                            "error": "Unable to load cost analytics data"
                        },
                        "cost_metrics": {},
                    }
                )

            return dashboard_data

        except Exception as e:
            logger.error(f"Error loading dashboard data: {e}")
            return {"error": str(e)}

    def get_optimized_dashboard_data(self, start_date, end_date, user_id):
        """Optimized data fetching for SSR"""

        # Use select_related and prefetch_related for efficient queries
        cache_key = f"dashboard_data_{start_date}_{end_date}_{user_id}"
        data = cache.get(cache_key)

        if not data:
            data = {
                "revenue": self._get_revenue_data_optimized(start_date, end_date),
                "costs": self._get_cost_data_optimized(start_date, end_date),
                "performance": self._get_performance_data_optimized(
                    start_date, end_date
                ),
            }

            # Cache for 5 minutes
            cache.set(cache_key, data, 300)

        return data

    def _get_revenue_data_optimized(self, start_date, end_date):
        """Optimized revenue query with prefetch"""
        from .revenue_analytics import RevenueAnalyticsService

        return (
            RevenueAnalyticsService()
            .get_revenue_overview(start_date, end_date)
            .select_related("category")
            .prefetch_related("products")
        )

    def _get_cost_data_optimized(self, start_date, end_date):
        """Optimized cost query with prefetch"""
        # Placeholder for cost optimization
        return {}

    def _get_performance_data_optimized(self, start_date, end_date):
        """Optimized performance query with prefetch"""
        # Placeholder for performance optimization
        return {}

    def get_recipe_stats(self):
        """Get recipe statistics"""
        try:
            recipes = Recipe.objects.filter(is_active=True)
            total_recipes = recipes.count()

            # Calculate average cost
            avg_cost = 0
            cost_efficiency = 0
            top_recipe = "N/A"

            if total_recipes > 0:
                # Calculate average cost from actual recipe data
                total_cost = sum(
                    recipe.total_cost_per_portion or Decimal("0")
                    for recipe in recipes
                    if recipe.total_cost_per_portion
                )
                avg_cost = (
                    total_cost / total_recipes if total_recipes > 0 else Decimal("0")
                )

                # Calculate cost efficiency (recipes with good profit margins)
                efficient_recipes = 0
                for recipe in recipes:
                    if (
                        recipe.actual_selling_price_per_portion
                        and recipe.total_cost_per_portion
                        and recipe.actual_selling_price_per_portion
                        > recipe.total_cost_per_portion
                    ):
                        profit_margin = (
                            (
                                recipe.actual_selling_price_per_portion
                                - recipe.total_cost_per_portion
                            )
                            / recipe.actual_selling_price_per_portion
                        ) * Decimal("100")
                        if profit_margin >= 40:  # 40% or higher profit margin
                            efficient_recipes += 1

                cost_efficiency = (
                    (efficient_recipes / total_recipes * Decimal("100"))
                    if total_recipes > 0
                    else Decimal("0")
                )

                # Find top recipe (highest profit margin)
                max_profit_margin = Decimal("0")
                for recipe in recipes:
                    if (
                        recipe.actual_selling_price_per_portion
                        and recipe.total_cost_per_portion
                        and recipe.actual_selling_price_per_portion
                        > recipe.total_cost_per_portion
                    ):
                        profit_margin = (
                            (
                                recipe.actual_selling_price_per_portion
                                - recipe.total_cost_per_portion
                            )
                            / recipe.actual_selling_price_per_portion
                        ) * Decimal("100")
                        if profit_margin > max_profit_margin:
                            max_profit_margin = profit_margin
                            top_recipe = recipe.dish_name

            return {
                "total_recipes": total_recipes,
                "avg_cost": avg_cost,
                "cost_efficiency": cost_efficiency,
                "top_recipe": top_recipe,
            }
        except Exception as e:
            logger.error(f"Error getting recipe stats: {e}")
            return {
                "total_recipes": 0,
                "avg_cost": 0,
                "cost_efficiency": 0,
                "top_recipe": "N/A",
            }

    def get_recipes_with_costs(self):
        """Get recipes with cost analysis"""
        try:
            recipes = Recipe.objects.filter(is_active=True).order_by("dish_name")[
                :10
            ]  # Limit to first 10 for performance
            recipes_with_costs = []

            for recipe in recipes:
                recipes_with_costs.append(
                    {
                        "pk": recipe.pk,
                        "dish_name": recipe.dish_name,
                        "description": recipe.description,
                        "category": recipe.category if recipe.category else "Other",
                        "total_cost_per_portion": (
                            recipe.total_cost_per_portion or Decimal("0")
                        ),
                        "suggested_selling_price_per_portion": (
                            recipe.suggested_selling_price_per_portion or Decimal("0")
                        ),
                        "actual_selling_price_per_portion": (
                            recipe.actual_selling_price_per_portion
                            if recipe.actual_selling_price_per_portion
                            else None
                        ),
                    }
                )

            return recipes_with_costs
        except Exception as e:
            logger.error(f"Error getting recipes with costs: {e}")
            return []

    def get_revenue_analytics_data(self, start_date, end_date):
        """Get comprehensive revenue analytics data"""
        try:
            # Get comprehensive revenue analysis
            revenue_overview = self.revenue_service.get_revenue_overview(
                start_date, end_date
            )
            top_categories = self.revenue_service.get_top_performing_categories(
                start_date, end_date
            )
            top_products = self.revenue_service.get_top_performing_products(
                start_date, end_date
            )
            time_analysis = self.revenue_service.get_time_based_analysis(
                start_date, end_date
            )
            growth_analysis = self.revenue_service.get_growth_analysis()
            opportunity_analysis = self.revenue_service.get_opportunity_analysis(
                start_date, end_date
            )
            payment_analysis = self.revenue_service.get_payment_method_analysis(
                start_date, end_date
            )

            return {
                "revenue_overview": revenue_overview,
                "top_categories": top_categories,
                "top_products": top_products,
                "time_analysis": time_analysis,
                "growth_analysis": growth_analysis,
                "opportunity_analysis": opportunity_analysis,
                "payment_analysis": payment_analysis,
            }
        except Exception as e:
            logger.error(f"Error getting revenue analytics data: {e}")
            return {"error": str(e)}

    def get_revenue_insights_data(self, start_date, end_date):
        """Get revenue insights and recommendations data"""
        try:
            # Get all analyses for comprehensive insights
            revenue_overview = self.revenue_service.get_revenue_overview(
                start_date, end_date
            )
            top_categories = self.revenue_service.get_top_performing_categories(
                start_date, end_date
            )
            top_products = self.revenue_service.get_top_performing_products(
                start_date, end_date
            )
            time_analysis = self.revenue_service.get_time_based_analysis(
                start_date, end_date
            )
            growth_analysis = self.revenue_service.get_growth_analysis()
            opportunity_analysis = self.revenue_service.get_opportunity_analysis(
                start_date, end_date
            )
            payment_analysis = self.revenue_service.get_payment_method_analysis(
                start_date, end_date
            )

            # Generate comprehensive insights
            insights = self._generate_comprehensive_insights(
                revenue_overview,
                top_categories,
                top_products,
                time_analysis,
                growth_analysis,
                opportunity_analysis,
                payment_analysis,
            )

            return {
                "revenue_overview": revenue_overview,
                "top_categories": top_categories,
                "top_products": top_products,
                "time_analysis": time_analysis,
                "growth_analysis": growth_analysis,
                "opportunity_analysis": opportunity_analysis,
                "payment_analysis": payment_analysis,
                "insights": insights,
            }
        except Exception as e:
            logger.error(f"Error getting revenue insights data: {e}")
            return {"error": str(e)}

    def _generate_comprehensive_insights(
        self,
        revenue_overview,
        top_categories,
        top_products,
        time_analysis,
        growth_analysis,
        opportunity_analysis,
        payment_analysis,
    ):
        """Generate comprehensive insights from all analyses"""
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

                high_margin = [p for p in products if p["estimated_profit_margin"] > 60]
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
            mobile_pct = payment_breakdown.get("mobile_money", {}).get("percentage", 0)

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

        return insights

    def _generate_recommendations(self, insights):
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

    def get_cost_analytics_data(self, start_date, end_date):
        """Get comprehensive cost analytics data for Chapter 3: Cost Chronicles"""
        try:
            # Get cost overview
            cost_overview = self.cost_service.get_cost_overview(start_date, end_date)

            # Get food cost analysis
            food_cost_analysis = self.cost_service.get_food_cost_analysis(
                start_date, end_date
            )

            # Get cost by category
            cost_by_category = self.cost_service.get_cost_by_category(
                start_date, end_date
            )

            # Get waste analysis
            waste_analysis = self.cost_service.get_waste_analysis(start_date, end_date)

            # Get recipe cost analysis
            recipe_cost_analysis = self.cost_service.get_recipe_cost_analysis(
                start_date, end_date
            )

            # Get cost optimization opportunities
            optimization_opportunities = (
                self.cost_service.get_cost_optimization_opportunities(
                    start_date, end_date
                )
            )

            # Get cost alerts
            cost_alerts = self.cost_service.get_cost_alerts(start_date, end_date)

            # Prepare cost analytics data
            cost_analytics = {
                "cost_overview": cost_overview,
                "food_cost_analysis": food_cost_analysis,
                "cost_by_category": cost_by_category,
                "waste_analysis": waste_analysis,
                "recipe_cost_analysis": recipe_cost_analysis,
                "optimization_opportunities": optimization_opportunities,
                "cost_alerts": cost_alerts,
            }

            # Extract key metrics for dashboard display
            cost_metrics = self._extract_cost_metrics(
                cost_overview, waste_analysis, cost_alerts
            )

            return {
                "cost_analytics": cost_analytics,
                "cost_metrics": cost_metrics,
            }

        except Exception as e:
            logger.error(f"Error getting cost analytics data: {e}")
            return {
                "cost_analytics": {"error": str(e)},
                "cost_metrics": {},
            }

    def _extract_cost_metrics(self, cost_overview, waste_analysis, cost_alerts):
        """Extract key cost metrics for dashboard display"""
        metrics = {}

        try:
            # Extract from cost overview
            if "error" not in cost_overview:
                overview = cost_overview
                metrics.update(
                    {
                        "total_food_cost": overview.get("total_metrics", {}).get(
                            "total_food_cost", 0
                        ),
                        "total_revenue": overview.get("total_metrics", {}).get(
                            "total_revenue", 0
                        ),
                        "food_cost_percentage": overview.get(
                            "percentage_metrics", {}
                        ).get("food_cost_percentage", 0),
                        "waste_cost_percentage": overview.get(
                            "percentage_metrics", {}
                        ).get("waste_cost_percentage", 0),
                        "gross_profit": overview.get("total_metrics", {}).get(
                            "gross_profit", 0
                        ),
                        "avg_daily_food_cost": overview.get("average_metrics", {}).get(
                            "avg_daily_food_cost", 0
                        ),
                        "avg_daily_revenue": overview.get("average_metrics", {}).get(
                            "avg_daily_revenue", 0
                        ),
                    }
                )

                # Performance grades
                performance = overview.get("performance_analysis", {})
                metrics.update(
                    {
                        "food_cost_grade": performance.get(
                            "food_cost_performance", {}
                        ).get("grade", "N/A"),
                        "waste_grade": performance.get("waste_performance", {}).get(
                            "grade", "N/A"
                        ),
                        "overall_grade": performance.get("overall_performance", {}).get(
                            "grade", "N/A"
                        ),
                        "overall_score": performance.get("overall_performance", {}).get(
                            "score", 0
                        ),
                    }
                )

            # Extract from waste analysis
            if "error" not in waste_analysis:
                waste = waste_analysis
                metrics.update(
                    {
                        "total_waste_cost": waste.get("total_waste_cost", 0),
                        "waste_percentage": waste.get("waste_percentage", 0),
                        "waste_efficiency_grade": waste.get("waste_efficiency", {}).get(
                            "efficiency_grade", "N/A"
                        ),
                    }
                )

            # Extract from cost alerts
            if "error" not in cost_alerts:
                alerts = cost_alerts
                summary = alerts.get("summary", {})
                metrics.update(
                    {
                        "critical_alerts_count": summary.get("critical_count", 0),
                        "warning_alerts_count": summary.get("warning_count", 0),
                        "info_alerts_count": summary.get("info_count", 0),
                    }
                )

            # Calculate additional metrics
            if metrics.get("total_revenue", 0) > 0:
                metrics["profit_margin"] = (
                    metrics["gross_profit"] / metrics["total_revenue"]
                ) * Decimal("100")
            else:
                metrics["profit_margin"] = Decimal("0")

        except Exception as e:
            logger.error(f"Error extracting cost metrics: {e}")
            metrics = {}

        return metrics

import logging
from datetime import date
from decimal import Decimal
from typing import Dict, List

from django.db.models import Avg, Count, Sum

from apps.analytics.models import DailySummary, ProductCostHistory
from apps.restaurant_data.models import Sales

logger = logging.getLogger(__name__)


class CostAnalyticsService:
    """
    Comprehensive cost analytics service for restaurant operations.

    Answers key cost questions:
    - "How much are we spending on ingredients?" → Food cost tracking
    - "Are our costs under control?" → Cost control analysis
    - "Where can we reduce costs?" → Cost optimization opportunities
    - "How efficient are our recipes?" → Recipe cost analysis
    - "What's causing waste?" → Waste cost analysis
    """

    # Industry benchmarks for Cameroon restaurant market
    COST_BENCHMARKS = {
        "food_cost_targets": {
            "excellent": (25, 30),  # 25-30% food cost
            "good": (30, 35),  # 30-35% food cost
            "acceptable": (35, 40),  # 35-40% food cost
            "high": (40, 50),  # 40-50% food cost
            "critical": (50, 100),  # 50%+ food cost
        },
        "waste_cost_targets": {
            "excellent": (0, 2),  # 0-2% of revenue
            "good": (2, 3),  # 2-3% of revenue
            "acceptable": (3, 5),  # 3-5% of revenue
            "high": (5, 10),  # 5-10% of revenue
            "critical": (10, 100),  # 10%+ of revenue
        },
        "cost_efficiency_targets": {
            "labor_cost_percentage": (20, 30),  # 20-30% of revenue
            "overhead_percentage": (15, 25),  # 15-25% of revenue
            "profit_margin_target": (15, 25),  # 15-25% net profit
        },
        "ingredient_cost_ranges": {
            "meat_proteins": (40, 60),  # 40-60% of food cost
            "vegetables": (15, 25),  # 15-25% of food cost
            "grains_starches": (10, 20),  # 10-20% of food cost
            "dairy": (8, 15),  # 8-15% of food cost
            "spices_condiments": (5, 10),  # 5-10% of food cost
        },
    }

    def __init__(self):
        self.errors = []
        self.warnings = []

    def get_cost_overview(self, start_date: date, end_date: date) -> Dict:
        """
        Get comprehensive cost overview for a date range.
        Answers: "How much are we spending on ingredients?"
        """
        try:
            # Get daily summaries for the period
            summaries = DailySummary.objects.filter(
                date__range=[start_date, end_date]
            ).order_by("date")

            if not summaries.exists():
                return {"error": "No data found for the specified period"}

            # Calculate key cost metrics
            total_food_cost = Decimal(
                str(summaries.aggregate(total=Sum("total_food_cost"))["total"] or 0)
            )

            total_revenue = Decimal(
                str(summaries.aggregate(total=Sum("total_sales"))["total"] or 0)
            )

            total_waste_cost = Decimal(
                str(summaries.aggregate(total=Sum("waste_cost"))["total"] or 0)
            )

            total_resale_cost = Decimal(
                str(summaries.aggregate(total=Sum("resale_cost"))["total"] or 0)
            )

            # Calculate averages
            days_count = summaries.count()

            try:
                avg_daily_food_cost = (
                    total_food_cost / Decimal(str(days_count))
                    if days_count > 0
                    else Decimal("0")
                )
                avg_daily_food_cost = (
                    total_food_cost / Decimal(str(days_count))
                    if days_count > 0
                    else Decimal("0")
                )
            except Exception as e:
                logger.error(f"Error calculating avg daily food cost: {e}")
                avg_daily_food_cost = Decimal("0")

            avg_daily_revenue = (
                total_revenue / Decimal(str(days_count))
                if days_count > 0
                else Decimal("0")
            )

            # Calculate percentages
            try:
                food_cost_percentage = (
                    (total_food_cost / total_revenue * Decimal("100"))
                    if total_revenue > 0
                    else Decimal("0")
                )
                food_cost_percentage = (
                    (total_food_cost / total_revenue * Decimal("100"))
                    if total_revenue > 0
                    else Decimal("0")
                )
            except Exception as e:
                logger.error(f"Error calculating food cost percentage: {e}")
                food_cost_percentage = Decimal("0")

            waste_cost_percentage = (
                (total_waste_cost / total_revenue * Decimal("100"))
                if total_revenue > 0
                else Decimal("0")
            )

            # Calculate cost trends
            cost_trends = self._calculate_cost_trends(summaries)

            # Performance analysis
            performance_analysis = self._analyze_cost_performance(
                food_cost_percentage, waste_cost_percentage, avg_daily_food_cost
            )

            # Cost alerts
            cost_alerts = self._generate_cost_alerts(summaries)

            return {
                "period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "days_count": days_count,
                },
                "total_metrics": {
                    "total_food_cost": total_food_cost,
                    "total_revenue": total_revenue,
                    "total_waste_cost": total_waste_cost,
                    "total_resale_cost": total_resale_cost,
                    "gross_profit": total_revenue - total_food_cost - total_resale_cost,
                },
                "percentage_metrics": {
                    "food_cost_percentage": food_cost_percentage,
                    "waste_cost_percentage": waste_cost_percentage,
                    "resale_cost_percentage": (
                        (total_resale_cost / total_revenue * Decimal("100"))
                        if total_revenue > 0
                        else Decimal("0")
                    ),
                },
                "average_metrics": {
                    "avg_daily_food_cost": avg_daily_food_cost,
                    "avg_daily_revenue": avg_daily_revenue,
                    "avg_daily_waste_cost": (
                        total_waste_cost / Decimal(str(days_count))
                        if days_count > 0
                        else Decimal("0")
                    ),
                },
                "cost_trends": cost_trends,
                "performance_analysis": performance_analysis,
                "cost_alerts": cost_alerts,
                "benchmark_comparison": self._compare_to_cost_benchmarks(
                    food_cost_percentage, waste_cost_percentage
                ),
            }

        except Exception as e:
            logger.error(f"Error getting cost overview: {e}")
            return {"error": str(e)}

    def get_food_cost_analysis(self, start_date: date, end_date: date) -> Dict:
        """
        Get detailed food cost analysis.
        Answers: "Are our costs under control?"
        """
        try:
            # Get daily summaries for the period
            summaries = DailySummary.objects.filter(
                date__range=[start_date, end_date]
            ).order_by("date")

            if not summaries.exists():
                return {"error": "No data found for the specified period"}

            # Daily food cost trends
            daily_food_costs = []
            for summary in summaries:
                daily_food_costs.append(
                    {
                        "date": summary.date,
                        "food_cost": summary.total_food_cost,
                        "food_cost_percentage": summary.food_cost_percentage,
                        "revenue": summary.total_sales,
                        "status": summary.food_cost_status,
                    }
                )

            # Food cost variance analysis
            variance_analysis = self._analyze_food_cost_variance(summaries)

            # Cost efficiency metrics
            efficiency_metrics = self._calculate_cost_efficiency_metrics(summaries)

            # Cost control indicators
            control_indicators = self._analyze_cost_control_indicators(summaries)

            return {
                "period": f"{start_date} to {end_date}",
                "daily_food_costs": daily_food_costs,
                "variance_analysis": variance_analysis,
                "efficiency_metrics": efficiency_metrics,
                "control_indicators": control_indicators,
                "insights": self._generate_food_cost_insights(daily_food_costs),
            }

        except Exception as e:
            logger.error(f"Error getting food cost analysis: {e}")
            return {"error": str(e)}

    def get_cost_by_category(self, start_date: date, end_date: date) -> Dict:
        """
        Get cost breakdown by ingredient category.
        Answers: "Where are our costs concentrated?"
        """
        try:
            # Get cost history data grouped by category
            category_costs = (
                ProductCostHistory.objects.filter(
                    purchase_date__date__range=[start_date, end_date]
                )
                .values("product_category__cost_type")
                .annotate(
                    total_cost=Sum("total_amount"),
                    total_quantity=Sum("recipe_quantity"),
                    avg_unit_cost=Avg("unit_cost_in_recipe_units"),
                    purchase_count=Count("id"),
                )
                .order_by("-total_cost")
            )

            # Calculate percentages
            total_cost = sum(item["total_cost"] for item in category_costs)

            categories = []
            for item in category_costs:
                percentage = (
                    (
                        Decimal(str(item["total_cost"]))
                        / Decimal(str(total_cost))
                        * Decimal("100")
                    )
                    if total_cost > 0
                    else Decimal("0")
                )
                categories.append(
                    {
                        "category_name": item["product_category__cost_type"]
                        or "Uncategorized",
                        "total_cost": item["total_cost"],
                        "total_quantity": item["total_quantity"],
                        "avg_unit_cost": item["avg_unit_cost"],
                        "purchase_count": item["purchase_count"],
                        "cost_percentage": percentage,
                        "performance_grade": self._grade_category_cost_performance(
                            percentage
                        ),
                    }
                )

            return {
                "period": f"{start_date} to {end_date}",
                "total_cost": total_cost,
                "categories": categories,
                "insights": self._generate_category_cost_insights(categories),
            }

        except Exception as e:
            logger.error(f"Error getting cost by category: {e}")
            return {"error": str(e)}

    def get_waste_analysis(self, start_date: date, end_date: date) -> Dict:
        """
        Get waste cost analysis.
        Answers: "What's causing waste?"
        """
        try:
            # Get daily summaries for the period
            summaries = DailySummary.objects.filter(
                date__range=[start_date, end_date]
            ).order_by("date")

            if not summaries.exists():
                return {"error": "No data found for the specified period"}

            # Calculate waste metrics
            total_waste_cost = summaries.aggregate(total=Sum("waste_cost"))[
                "total"
            ] or Decimal("0")
            total_revenue = summaries.aggregate(total=Sum("total_sales"))[
                "total"
            ] or Decimal("0")

            # Daily waste trends
            daily_waste = []
            for summary in summaries:
                waste_percentage = (
                    (summary.waste_cost / summary.total_sales * Decimal("100"))
                    if summary.total_sales > 0
                    else Decimal("0")
                )
                daily_waste.append(
                    {
                        "date": summary.date,
                        "waste_cost": summary.waste_cost,
                        "waste_percentage": waste_percentage,
                        "revenue": summary.total_sales,
                        "status": self._get_waste_status(waste_percentage),
                    }
                )

            # Waste efficiency analysis
            waste_efficiency = self._analyze_waste_efficiency(summaries)

            # Waste reduction opportunities
            reduction_opportunities = self._identify_waste_reduction_opportunities(
                summaries
            )

            return {
                "period": f"{start_date} to {end_date}",
                "total_waste_cost": total_waste_cost,
                "waste_percentage": (
                    (total_waste_cost / total_revenue * Decimal("100"))
                    if total_revenue > 0
                    else Decimal("0")
                ),
                "daily_waste": daily_waste,
                "waste_efficiency": waste_efficiency,
                "reduction_opportunities": reduction_opportunities,
                "insights": self._generate_waste_insights(daily_waste),
            }

        except Exception as e:
            logger.error(f"Error getting waste analysis: {e}")
            return {"error": str(e)}

    def get_recipe_cost_analysis(self, start_date: date, end_date: date) -> Dict:
        """
        Get recipe cost analysis.
        Answers: "How efficient are our recipes?"
        """
        try:
            # Get sales data with product costs
            recipe_sales = (
                Sales.objects.filter(sale_date__range=[start_date, end_date])
                .values(
                    "product__name",
                    "product__sales_category__name",
                    "product__current_cost_per_unit",
                )
                .annotate(
                    total_revenue=Sum("total_sale_price"),
                    total_quantity=Sum("quantity_sold"),
                )
                .order_by("-total_revenue")
            )

            recipes = []
            for item in recipe_sales:
                # Calculate profit margin
                total_cost = Decimal(str(item["total_quantity"])) * (
                    Decimal(str(item["product__current_cost_per_unit"]))
                    if item["product__current_cost_per_unit"]
                    else Decimal("0")
                )
                total_revenue = Decimal(str(item["total_revenue"]))

                if total_revenue > 0:
                    profit_margin = (
                        (total_revenue - total_cost) / total_revenue
                    ) * Decimal("100")
                else:
                    profit_margin = Decimal("0")

                # Calculate cost per portion
                avg_unit_cost = (
                    Decimal(str(item.get("product__current_cost_per_unit", 0)))
                    if item.get("product__current_cost_per_unit", 0)
                    else Decimal("0")
                )
                avg_unit_price = (
                    total_revenue / Decimal(str(item["total_quantity"]))
                    if Decimal(str(item["total_quantity"])) > 0
                    else Decimal("0")
                )

                recipes.append(
                    {
                        "recipe_name": item["product__name"],
                        "category": item["product__sales_category__name"]
                        or "Uncategorized",
                        "total_revenue": total_revenue,
                        "total_cost": total_cost,
                        "total_quantity": Decimal(str(item["total_quantity"])),
                        "avg_unit_cost": avg_unit_cost,
                        "avg_unit_price": avg_unit_price,
                        "profit_margin": profit_margin,
                        "cost_efficiency": self._calculate_recipe_cost_efficiency(
                            avg_unit_cost, avg_unit_price
                        ),
                        "performance_grade": self._grade_recipe_performance(
                            profit_margin
                        ),
                    }
                )

            return {
                "period": f"{start_date} to {end_date}",
                "recipes": recipes,
                "insights": self._generate_recipe_cost_insights(recipes),
            }

        except Exception as e:
            logger.error(f"Error getting recipe cost analysis: {e}")
            return {"error": str(e)}

    def get_cost_optimization_opportunities(
        self, start_date: date, end_date: date
    ) -> Dict:
        """
        Get cost optimization opportunities.
        Answers: "Where can we reduce costs?"
        """
        try:
            # High-cost ingredients
            high_cost_ingredients = self._identify_high_cost_ingredients(
                start_date, end_date
            )

            # Low-margin recipes
            low_margin_recipes = self._identify_low_margin_recipes(start_date, end_date)

            # Waste reduction opportunities
            waste_opportunities = self._identify_waste_reduction_opportunities(
                DailySummary.objects.filter(date__range=[start_date, end_date])
            )

            # Bulk purchasing opportunities
            bulk_opportunities = self._identify_bulk_purchasing_opportunities(
                start_date, end_date
            )

            # Seasonal cost variations
            seasonal_variations = self._analyze_seasonal_cost_variations(
                start_date, end_date
            )

            return {
                "period": f"{start_date} to {end_date}",
                "high_cost_ingredients": high_cost_ingredients,
                "low_margin_recipes": low_margin_recipes,
                "waste_opportunities": waste_opportunities,
                "bulk_opportunities": bulk_opportunities,
                "seasonal_variations": seasonal_variations,
                "actionable_insights": self._generate_optimization_insights(
                    high_cost_ingredients,
                    low_margin_recipes,
                    waste_opportunities,
                ),
            }

        except Exception as e:
            logger.error(f"Error getting cost optimization opportunities: {e}")
            return {"error": str(e)}

    def get_cost_alerts(self, start_date: date, end_date: date) -> Dict:
        """
        Get cost control alerts and warnings.
        """
        try:
            summaries = DailySummary.objects.filter(
                date__range=[start_date, end_date]
            ).order_by("date")

            if not summaries.exists():
                return {"error": "No data found for the specified period"}

            alerts = {
                "critical": [],
                "warning": [],
                "info": [],
            }

            # Check for critical alerts
            for summary in summaries:
                # High food cost alert
                food_cost_pct = Decimal(str(summary.food_cost_percentage or 0))
                if food_cost_pct > Decimal("40"):
                    alerts["critical"].append(
                        {
                            "date": summary.date,
                            "type": "high_food_cost",
                            "message": f"Food cost {food_cost_pct:.1f}% exceeds 40% threshold",
                            "value": food_cost_pct,
                            "threshold": 40,
                        }
                    )

                # High waste cost alert
                waste_percentage = (
                    (summary.waste_cost / summary.total_sales * Decimal("100"))
                    if summary.total_sales > 0
                    else Decimal("0")
                )
                if waste_percentage > Decimal("5"):
                    alerts["critical"].append(
                        {
                            "date": summary.date,
                            "type": "high_waste_cost",
                            "message": f"Waste cost {waste_percentage:.1f}% exceeds 5% threshold",
                            "value": waste_percentage,
                            "threshold": 5,
                        }
                    )

                # Warning alerts
                if Decimal("35") < food_cost_pct <= Decimal("40"):
                    alerts["warning"].append(
                        {
                            "date": summary.date,
                            "type": "elevated_food_cost",
                            "message": f"Food cost {food_cost_pct:.1f}% is elevated",
                            "value": food_cost_pct,
                            "threshold": 35,
                        }
                    )

                if Decimal("3") < waste_percentage <= Decimal("5"):
                    alerts["warning"].append(
                        {
                            "date": summary.date,
                            "type": "elevated_waste_cost",
                            "message": f"Waste cost {waste_percentage:.1f}% is elevated",
                            "value": waste_percentage,
                            "threshold": 3,
                        }
                    )

            return {
                "period": f"{start_date} to {end_date}",
                "alerts": alerts,
                "summary": {
                    "critical_count": len(alerts["critical"]),
                    "warning_count": len(alerts["warning"]),
                    "info_count": len(alerts["info"]),
                },
            }

        except Exception as e:
            logger.error(f"Error getting cost alerts: {e}")
            return {"error": str(e)}

    def get_cost_analytics_data(self, start_date, end_date):
        """Get comprehensive cost analytics data for Chapter 3: Cost Chronicles"""
        try:
            # Get cost overview
            cost_overview = self.get_cost_overview(start_date, end_date)

            # Get food cost analysis
            food_cost_analysis = self.get_food_cost_analysis(start_date, end_date)

            # Get cost by category
            cost_by_category = self.get_cost_by_category(start_date, end_date)

            # Get waste analysis
            waste_analysis = self.get_waste_analysis(start_date, end_date)

            # Get recipe cost analysis
            recipe_cost_analysis = self.get_recipe_cost_analysis(start_date, end_date)

            # Get cost optimization opportunities
            optimization_opportunities = self.get_cost_optimization_opportunities(
                start_date, end_date
            )

            # Get cost alerts
            cost_alerts = self.get_cost_alerts(start_date, end_date)

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

    # === PRIVATE HELPER METHODS ===

    def _calculate_cost_trends(self, summaries) -> Dict:
        """Calculate cost trends over time"""
        daily_data = []
        for summary in summaries:
            daily_data.append(
                {
                    "date": summary.date,
                    "food_cost": summary.total_food_cost,
                    "food_cost_percentage": summary.food_cost_percentage,
                    "waste_cost": summary.waste_cost,
                    "revenue": summary.total_sales,
                }
            )

        return {
            "daily_data": daily_data,
            "trend_direction": self._determine_cost_trend_direction(daily_data),
        }

    def _analyze_cost_performance(
        self,
        food_cost_percentage: Decimal,
        waste_cost_percentage: Decimal,
        avg_daily_food_cost: Decimal,
    ) -> Dict:
        """Analyze cost performance against benchmarks"""
        # Food cost performance
        if food_cost_percentage <= Decimal("30"):
            food_cost_grade = "A"
            food_cost_score = Decimal("100")
        elif food_cost_percentage <= Decimal("35"):
            food_cost_grade = "B"
            food_cost_score = Decimal("80")
        elif food_cost_percentage <= Decimal("40"):
            food_cost_grade = "C"
            food_cost_score = Decimal("60")
        elif food_cost_percentage <= Decimal("50"):
            food_cost_grade = "D"
            food_cost_score = Decimal("40")
        else:
            food_cost_grade = "F"
            food_cost_score = Decimal("20")

        # Waste cost performance
        if waste_cost_percentage <= Decimal("2"):
            waste_grade = "A"
            waste_score = Decimal("100")
        elif waste_cost_percentage <= Decimal("3"):
            waste_grade = "B"
            waste_score = Decimal("80")
        elif waste_cost_percentage <= Decimal("5"):
            waste_grade = "C"
            waste_score = Decimal("60")
        elif waste_cost_percentage <= Decimal("10"):
            waste_grade = "D"
            waste_score = Decimal("40")
        else:
            waste_grade = "F"
            waste_score = Decimal("20")

        # Overall performance score (weighted average)
        overall_score = (food_cost_score * Decimal("0.7")) + (
            waste_score * Decimal("0.3")
        )

        return {
            "food_cost_performance": {
                "grade": food_cost_grade,
                "score": food_cost_score,
                "percentage": food_cost_percentage,
            },
            "waste_performance": {
                "grade": waste_grade,
                "score": waste_score,
                "percentage": waste_cost_percentage,
            },
            "overall_performance": {
                "score": overall_score,
                "grade": self._grade_performance(overall_score),
            },
        }

    def _analyze_food_cost_variance(self, summaries) -> Dict:
        """Analyze food cost variance"""
        if not summaries:
            return {}

        # Calculate average food cost percentage
        avg_food_cost_pct = Decimal(
            str(summaries.aggregate(avg=Avg("food_cost_percentage"))["avg"] or 0)
        )

        # Calculate variance
        variances = []
        for summary in summaries:
            food_cost_pct = Decimal(str(summary.food_cost_percentage or 0))
            variance = food_cost_pct - avg_food_cost_pct
            variances.append(variance)

        # Find high variance days
        high_variance_days = []
        for summary in summaries:
            food_cost_pct = Decimal(str(summary.food_cost_percentage or 0))
            variance = food_cost_pct - avg_food_cost_pct
            if abs(variance) > Decimal("5"):  # More than 5% variance
                high_variance_days.append(
                    {
                        "date": summary.date,
                        "food_cost_percentage": food_cost_pct,
                        "variance": variance,
                        "reason": "High variance from average",
                    }
                )

        return {
            "average_food_cost_percentage": avg_food_cost_pct,
            "variance_range": {
                "min": min(variances) if variances else 0,
                "max": max(variances) if variances else 0,
            },
            "high_variance_days": high_variance_days,
        }

    def _calculate_cost_efficiency_metrics(self, summaries) -> Dict:
        """Calculate cost efficiency metrics"""
        if not summaries:
            return {}

        # Ensure all values are Decimal to avoid type errors
        total_revenue = sum(Decimal(str(s.total_sales or 0)) for s in summaries)
        total_food_cost = sum(Decimal(str(s.total_food_cost or 0)) for s in summaries)
        total_waste_cost = sum(Decimal(str(s.waste_cost or 0)) for s in summaries)

        return {
            "cost_per_revenue_ratio": (
                total_food_cost / total_revenue if total_revenue > 0 else Decimal("0")
            ),
            "waste_per_revenue_ratio": (
                total_waste_cost / total_revenue if total_revenue > 0 else Decimal("0")
            ),
            "efficiency_score": self._calculate_efficiency_score(
                total_food_cost, total_waste_cost, total_revenue
            ),
        }

    def _analyze_cost_control_indicators(self, summaries) -> Dict:
        """Analyze cost control indicators"""
        if not summaries:
            return {}

        # Count days by food cost status
        status_counts = {}
        for summary in summaries:
            status = summary.food_cost_status
            status_counts[status] = status_counts.get(status, 0) + 1

        # Calculate control percentage
        total_days = len(summaries)
        controlled_days = status_counts.get("excellent", 0) + status_counts.get(
            "good", 0
        )
        control_percentage = (
            (Decimal(str(controlled_days)) / Decimal(str(total_days)) * Decimal("100"))
            if total_days > 0
            else Decimal("0")
        )

        return {
            "status_breakdown": status_counts,
            "control_percentage": control_percentage,
            "control_grade": self._grade_performance(control_percentage),
        }

    def _analyze_waste_efficiency(self, summaries) -> Dict:
        """Analyze waste efficiency"""
        if not summaries:
            return {}

        # Ensure all values are Decimal to avoid type errors
        total_waste_cost = sum(Decimal(str(s.waste_cost or 0)) for s in summaries)
        total_revenue = sum(Decimal(str(s.total_sales or 0)) for s in summaries)
        total_food_cost = sum(Decimal(str(s.total_food_cost or 0)) for s in summaries)

        waste_percentage = (
            (total_waste_cost / total_revenue * Decimal("100"))
            if total_revenue > 0
            else Decimal("0")
        )
        waste_to_food_cost_ratio = (
            (total_waste_cost / total_food_cost * Decimal("100"))
            if total_food_cost > 0
            else Decimal("0")
        )

        return {
            "waste_percentage": waste_percentage,
            "waste_to_food_cost_ratio": waste_to_food_cost_ratio,
            "efficiency_grade": self._grade_waste_efficiency(waste_percentage),
        }

    def _identify_waste_reduction_opportunities(self, summaries) -> List[Dict]:
        """Identify waste reduction opportunities"""
        opportunities = []

        if not summaries:
            return opportunities

        # Find high waste days
        for summary in summaries:
            waste_cost = Decimal(str(summary.waste_cost or 0))
            total_sales = Decimal(str(summary.total_sales or 0))
            waste_percentage = (
                (waste_cost / total_sales * Decimal("100"))
                if total_sales > 0
                else Decimal("0")
            )
            if waste_percentage > Decimal("3"):
                opportunities.append(
                    {
                        "date": summary.date,
                        "type": "high_waste_day",
                        "waste_cost": summary.waste_cost,
                        "waste_percentage": waste_percentage,
                        "suggestion": "Review prep quantities and portion control",
                    }
                )

        return opportunities

    def _identify_high_cost_ingredients(
        self, start_date: date, end_date: date
    ) -> List[Dict]:
        """Identify high-cost ingredients"""
        high_cost_ingredients = []

        # Get cost history for the period
        cost_history = ProductCostHistory.objects.filter(
            purchase_date__date__range=[start_date, end_date]
        ).select_related("product", "product_category")

        # Group by product and calculate average cost
        product_costs = {}
        for record in cost_history:
            product_name = record.product.name
            if product_name not in product_costs:
                product_costs[product_name] = {
                    "total_cost": 0.0,
                    "total_quantity": 0.0,
                    "purchase_count": 0,
                    "category": record.product_category.cost_type,
                }

            product_costs[product_name]["total_cost"] += record.total_amount or Decimal(
                "0"
            )
            product_costs[product_name][
                "total_quantity"
            ] += record.recipe_quantity or Decimal("0")
            product_costs[product_name]["purchase_count"] += 1

        # Calculate average unit costs and identify high-cost items
        for product_name, data in product_costs.items():
            avg_unit_cost = (
                data["total_cost"] / data["total_quantity"]
                if data["total_quantity"] > 0
                else Decimal("0")
            )

            # Consider high cost if > 1000 FCFA per unit (adjustable threshold)
            if avg_unit_cost > Decimal("1000"):
                high_cost_ingredients.append(
                    {
                        "ingredient_name": product_name,
                        "category": data["category"],
                        "avg_unit_cost": avg_unit_cost,
                        "total_cost": data["total_cost"],
                        "purchase_count": data["purchase_count"],
                        "suggestion": "Consider bulk purchasing or alternative suppliers",
                    }
                )

        return sorted(
            high_cost_ingredients, key=lambda x: x["avg_unit_cost"], reverse=True
        )

    def _identify_low_margin_recipes(
        self, start_date: date, end_date: date
    ) -> List[Dict]:
        """Identify low-margin recipes"""
        low_margin_recipes = []

        # Get sales data with costs
        sales_data = (
            Sales.objects.filter(sale_date__range=[start_date, end_date])
            .values("product__name", "product__current_cost_per_unit")
            .annotate(
                total_revenue=Sum("total_sale_price"),
                total_quantity=Sum("quantity_sold"),
            )
        )

        for item in sales_data:
            total_cost = Decimal(str(item["total_quantity"])) * (
                Decimal(str(item["product__current_cost_per_unit"]))
                if item["product__current_cost_per_unit"]
                else Decimal("0")
            )
            total_revenue = Decimal(str(item["total_revenue"]))

            if total_revenue > 0:
                profit_margin = (
                    (total_revenue - total_cost) / total_revenue
                ) * Decimal("100")

                # Consider low margin if < 50% (adjustable threshold)
                if profit_margin < Decimal("50"):
                    low_margin_recipes.append(
                        {
                            "recipe_name": item["product__name"],
                            "profit_margin": profit_margin,
                            "total_revenue": total_revenue,
                            "total_cost": total_cost,
                            "suggestion": "Review pricing or reduce ingredient costs",
                        }
                    )

        return sorted(low_margin_recipes, key=lambda x: x["profit_margin"])

    def _identify_bulk_purchasing_opportunities(
        self, start_date: date, end_date: date
    ) -> List[Dict]:
        """Identify bulk purchasing opportunities"""
        opportunities = []

        # Get frequently purchased items
        purchase_frequency = (
            ProductCostHistory.objects.filter(
                purchase_date__date__range=[start_date, end_date]
            )
            .values("product__name")
            .annotate(
                purchase_count=Count("id"),
                total_cost=Sum("total_amount"),
                avg_unit_cost=Avg("unit_cost_in_recipe_units"),
            )
            .filter(purchase_count__gte=3)  # Purchased 3+ times in period
            .order_by("-purchase_count")
        )

        for item in purchase_frequency:
            opportunities.append(
                {
                    "ingredient_name": item["product__name"],
                    "purchase_count": item["purchase_count"],
                    "total_cost": item["total_cost"],
                    "avg_unit_cost": item["avg_unit_cost"],
                    "suggestion": "Consider bulk purchasing for better pricing",
                }
            )

        return opportunities

    def _analyze_seasonal_cost_variations(
        self, start_date: date, end_date: date
    ) -> Dict:
        """Analyze seasonal cost variations"""
        # This would require historical data over multiple periods
        # For now, return a placeholder structure
        return {
            "note": "Seasonal analysis requires historical data over multiple periods",
            "recommendation": "Track costs over 12+ months for seasonal patterns",
        }

    def _determine_cost_trend_direction(self, daily_data: List[Dict]) -> str:
        """Determine overall cost trend direction"""
        if len(daily_data) < 2:
            return "insufficient_data"

        # Simple trend analysis
        first_half = daily_data[: len(daily_data) // 2]
        second_half = daily_data[len(daily_data) // 2 :]

        first_avg = (
            sum(d["food_cost_percentage"] for d in first_half)
            / Decimal(str(len(first_half)))
            if first_half
            else Decimal("0")
        )
        second_avg = (
            sum(d["food_cost_percentage"] for d in second_half)
            / Decimal(str(len(second_half)))
            if second_half
            else Decimal("0")
        )

        if second_avg > first_avg * Decimal("1.05"):
            return "increasing"
        elif second_avg < first_avg * Decimal("0.95"):
            return "decreasing"
        else:
            return "stable"

    def _compare_to_cost_benchmarks(
        self, food_cost_percentage: Decimal, waste_cost_percentage: Decimal
    ) -> Dict:
        """Compare costs to industry benchmarks"""
        comparisons = {}

        # Food cost comparison
        for level, (min_target, max_target) in self.COST_BENCHMARKS[
            "food_cost_targets"
        ].items():
            if min_target <= food_cost_percentage <= max_target:
                comparisons["food_cost"] = level
                break

        # Waste cost comparison
        for level, (min_target, max_target) in self.COST_BENCHMARKS[
            "waste_cost_targets"
        ].items():
            if min_target <= waste_cost_percentage <= max_target:
                comparisons["waste_cost"] = level
                break

        return comparisons

    def _grade_category_cost_performance(self, cost_percentage: Decimal) -> str:
        """Grade category cost performance"""
        if cost_percentage >= Decimal("30"):
            return "A"
        elif cost_percentage >= Decimal("20"):
            return "B"
        elif cost_percentage >= Decimal("10"):
            return "C"
        elif cost_percentage >= Decimal("5"):
            return "D"
        else:
            return "F"

    def _grade_recipe_performance(self, profit_margin: Decimal) -> str:
        """Grade recipe performance based on profit margin"""
        if profit_margin >= Decimal("70"):
            return "A"
        elif profit_margin >= Decimal("60"):
            return "B"
        elif profit_margin >= Decimal("50"):
            return "C"
        elif profit_margin >= Decimal("40"):
            return "D"
        else:
            return "F"

    def _grade_performance(self, score: Decimal) -> str:
        """Grade overall performance"""
        if score >= Decimal("90"):
            return "A"
        elif score >= Decimal("80"):
            return "B"
        elif score >= Decimal("70"):
            return "C"
        elif score >= Decimal("60"):
            return "D"
        else:
            return "F"

    def _grade_waste_efficiency(self, waste_percentage: Decimal) -> str:
        """Grade waste efficiency"""
        if waste_percentage <= Decimal("2"):
            return "A"
        elif waste_percentage <= Decimal("3"):
            return "B"
        elif waste_percentage <= Decimal("5"):
            return "C"
        elif waste_percentage <= Decimal("10"):
            return "D"
        else:
            return "F"

    def _get_waste_status(self, waste_percentage: Decimal) -> str:
        """Get waste status"""
        if waste_percentage <= Decimal("2"):
            return "excellent"
        elif waste_percentage <= Decimal("3"):
            return "good"
        elif waste_percentage <= Decimal("5"):
            return "acceptable"
        else:
            return "high"

    def _calculate_recipe_cost_efficiency(
        self, unit_cost: Decimal, unit_price: Decimal
    ) -> Decimal:
        """Calculate recipe cost efficiency"""
        if unit_price > 0:
            return (unit_cost / unit_price) * Decimal("100")
        return Decimal("0")

    def _calculate_efficiency_score(
        self,
        total_food_cost: Decimal,
        total_waste_cost: Decimal,
        total_revenue: Decimal,
    ) -> Decimal:
        """Calculate overall efficiency score"""
        if total_revenue == 0:
            return Decimal("0")

        food_cost_efficiency = Decimal("100") - (
            total_food_cost / total_revenue * Decimal("100")
        )
        waste_efficiency = Decimal("100") - (
            total_waste_cost / total_revenue * Decimal("100")
        )

        # Weighted average (70% food cost, 30% waste)
        return (food_cost_efficiency * Decimal("0.7")) + (
            waste_efficiency * Decimal("0.3")
        )

    # === INSIGHT GENERATION METHODS ===

    def _generate_food_cost_insights(self, daily_food_costs: List[Dict]) -> List[str]:
        """Generate insights from food cost analysis"""
        insights = []

        if not daily_food_costs:
            return insights

        # Analyze trends
        high_cost_days = [
            d for d in daily_food_costs if d["food_cost_percentage"] > Decimal("35")
        ]
        if high_cost_days:
            insights.append(
                f"{len(high_cost_days)} days had food costs above 35% - review portion control"
            )

        # Analyze consistency
        percentages = [d["food_cost_percentage"] for d in daily_food_costs]
        variance = max(percentages) - min(percentages) if percentages else Decimal("0")
        if variance > Decimal("10"):
            insights.append(
                f"High food cost variance ({variance:.1f}%) - standardize recipes and portions"
            )

        return insights

    def _generate_category_cost_insights(self, categories: List[Dict]) -> List[str]:
        """Generate insights from category cost analysis"""
        insights = []

        if not categories:
            return insights

        # Identify highest cost category
        top_category = categories[0]
        if top_category["cost_percentage"] > Decimal("40"):
            insights.append(
                f"{top_category['category_name']} represents {top_category['cost_percentage']:.1f}% of costs - consider alternatives"
            )

        # Identify low-cost categories
        low_cost_categories = [
            c for c in categories if c["cost_percentage"] < Decimal("5")
        ]
        if low_cost_categories:
            insights.append(
                f"{len(low_cost_categories)} categories are under 5% of total costs"
            )

        return insights

    def _generate_waste_insights(self, daily_waste: List[Dict]) -> List[str]:
        """Generate insights from waste analysis"""
        insights = []

        if not daily_waste:
            return insights

        # Analyze high waste days
        high_waste_days = [
            d for d in daily_waste if d["waste_percentage"] > Decimal("3")
        ]
        if high_waste_days:
            insights.append(
                f"{len(high_waste_days)} days had waste above 3% - review prep quantities"
            )

        # Analyze waste trends
        waste_percentages = [d["waste_percentage"] for d in daily_waste]
        avg_waste = (
            sum(waste_percentages) / len(waste_percentages)
            if waste_percentages
            else Decimal("0")
        )
        if avg_waste > Decimal("2"):
            insights.append(
                f"Average waste is {avg_waste:.1f}% - implement waste tracking"
            )

        return insights

    def _generate_recipe_cost_insights(self, recipes: List[Dict]) -> List[str]:
        """Generate insights from recipe cost analysis"""
        insights = []

        if not recipes:
            return insights

        # Identify high-margin recipes
        high_margin = [r for r in recipes if r["profit_margin"] > Decimal("70")]
        if high_margin:
            insights.append(
                f"{len(high_margin)} recipes have excellent profit margins (>70%)"
            )

        # Identify low-margin recipes
        low_margin = [r for r in recipes if r["profit_margin"] < Decimal("50")]
        if low_margin:
            insights.append(
                f"{len(low_margin)} recipes have low profit margins (<50%) - review pricing"
            )

        return insights

    def _generate_optimization_insights(
        self,
        high_cost_ingredients: List,
        low_margin_recipes: List,
        waste_opportunities: List,
    ) -> List[str]:
        """Generate optimization insights"""
        insights = []

        if high_cost_ingredients:
            insights.append(
                f"{len(high_cost_ingredients)} high-cost ingredients identified for bulk purchasing"
            )

        if low_margin_recipes:
            insights.append(
                f"{len(low_margin_recipes)} recipes need pricing or cost optimization"
            )

        if waste_opportunities:
            insights.append(
                f"{len(waste_opportunities)} waste reduction opportunities identified"
            )

        if not insights:
            insights.append("All cost areas are performing well within targets")

        return insights

    def _generate_cost_alerts(self, summaries) -> List[Dict]:
        """Generate cost alerts from daily summaries"""
        alerts = []

        for summary in summaries:
            # High food cost alert
            food_cost_pct = summary.food_cost_percentage
            if food_cost_pct > Decimal("40"):
                alerts.append(
                    {
                        "date": summary.date,
                        "type": "critical",
                        "message": f"Food cost {food_cost_pct:.1f}% exceeds 40%",
                        "value": food_cost_pct,
                    }
                )
            elif food_cost_pct > Decimal("35"):
                alerts.append(
                    {
                        "date": summary.date,
                        "type": "warning",
                        "message": f"Food cost {food_cost_pct:.1f}% is elevated",
                        "value": food_cost_pct,
                    }
                )

            # High waste alert
            waste_cost = Decimal(str(summary.waste_cost or 0))
            total_sales = Decimal(str(summary.total_sales or 0))
            waste_percentage = (
                (waste_cost / total_sales * Decimal("100"))
                if total_sales > 0
                else Decimal("0")
            )
            if waste_percentage > Decimal("5"):
                alerts.append(
                    {
                        "date": summary.date,
                        "type": "critical",
                        "message": f"Waste cost {waste_percentage:.1f}% exceeds 5%",
                        "value": waste_percentage,
                    }
                )

        return alerts

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
                            "total_food_cost", Decimal("0")
                        ),
                        "total_revenue": overview.get("total_metrics", {}).get(
                            "total_revenue", Decimal("0")
                        ),
                        "food_cost_percentage": overview.get(
                            "percentage_metrics", {}
                        ).get("food_cost_percentage", Decimal("0")),
                        "waste_cost_percentage": overview.get(
                            "percentage_metrics", {}
                        ).get("waste_cost_percentage", Decimal("0")),
                        "gross_profit": overview.get("total_metrics", {}).get(
                            "gross_profit", Decimal("0")
                        ),
                        "avg_daily_food_cost": overview.get("average_metrics", {}).get(
                            "avg_daily_food_cost", Decimal("0")
                        ),
                        "avg_daily_revenue": overview.get("average_metrics", {}).get(
                            "avg_daily_revenue", Decimal("0")
                        ),
                    }
                )

                # Performance grades
                performance = overview.get("performance_analysis", {})
                metrics.update(
                    {
                        "food_cost_grade": performance.get("food_cost_grade", "N/A"),
                        "waste_grade": performance.get("waste_grade", "N/A"),
                        "overall_grade": performance.get("overall_performance", {}).get(
                            "grade", "N/A"
                        ),
                    }
                )

            # Extract from waste analysis
            if waste_analysis and "error" not in waste_analysis:
                metrics.update(
                    {
                        "total_waste_cost": waste_analysis.get(
                            "total_waste_cost", Decimal("0")
                        ),
                        "waste_percentage": waste_analysis.get(
                            "waste_percentage", Decimal("0")
                        ),
                    }
                )

            # Extract from cost alerts
            if cost_alerts:
                metrics.update(
                    {
                        "critical_alerts": len(
                            cost_alerts.get("alerts", {}).get("critical", [])
                        ),
                        "warning_alerts": len(
                            cost_alerts.get("alerts", {}).get("warning", [])
                        ),
                        "info_alerts": len(
                            cost_alerts.get("alerts", {}).get("info", [])
                        ),
                        "critical_alerts_count": len(
                            cost_alerts.get("alerts", {}).get("critical", [])
                        ),
                        "warning_alerts_count": len(
                            cost_alerts.get("alerts", {}).get("warning", [])
                        ),
                    }
                )

            # Calculate missing fields that the template expects
            # Overall score calculation
            if "food_cost_percentage" in metrics and "waste_percentage" in metrics:
                food_cost_score = 100 - (
                    metrics["food_cost_percentage"] * 2
                )  # Lower is better
                waste_score = 100 - (
                    metrics["waste_percentage"] * 10
                )  # Lower is better
                metrics["overall_score"] = max(0, (food_cost_score + waste_score) / 2)
            else:
                metrics["overall_score"] = Decimal("0")

            # Profit margin calculation
            if "gross_profit" in metrics and "total_revenue" in metrics:
                if metrics["total_revenue"] > 0:
                    metrics["profit_margin"] = (
                        metrics["gross_profit"] / metrics["total_revenue"]
                    ) * 100
                else:
                    metrics["profit_margin"] = Decimal("0")
            else:
                metrics["profit_margin"] = Decimal("0")

        except Exception as e:
            logger.error(f"Error extracting cost metrics: {e}")
            metrics = {}

        return metrics

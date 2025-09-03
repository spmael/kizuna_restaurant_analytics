import logging
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

from django.db.models import Avg, Sum

from apps.analytics.models import DailySummary

logger = logging.getLogger(__name__)


class CostUtils:
    """
    Utility functions for cost analytics and calculations.

    Provides helper functions for:
    - Cost calculations and formatting
    - Cost trend analysis
    - Cost benchmarking
    - Cost alert generation
    - Cost data validation
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
    }

    @staticmethod
    def calculate_food_cost_percentage(food_cost: Decimal, revenue: Decimal) -> float:
        """
        Calculate food cost percentage.

        Args:
            food_cost: Total food cost
            revenue: Total revenue

        Returns:
            Food cost percentage (0-100)
        """
        if revenue <= 0:
            return 0.0

        return float((food_cost / revenue) * 100)

    @staticmethod
    def calculate_waste_cost_percentage(waste_cost: Decimal, revenue: Decimal) -> float:
        """
        Calculate waste cost percentage.

        Args:
            waste_cost: Total waste cost
            revenue: Total revenue

        Returns:
            Waste cost percentage (0-100)
        """
        if revenue <= 0:
            return 0.0

        return float((waste_cost / revenue) * 100)

    @staticmethod
    def calculate_profit_margin(revenue: Decimal, cost: Decimal) -> float:
        """
        Calculate profit margin percentage.

        Args:
            revenue: Total revenue
            cost: Total cost

        Returns:
            Profit margin percentage (0-100)
        """
        if revenue <= 0:
            return 0.0

        return float(((revenue - cost) / revenue) * 100)

    @staticmethod
    def calculate_cost_per_portion(total_cost: Decimal, portions: int) -> Decimal:
        """
        Calculate cost per portion.

        Args:
            total_cost: Total cost of the recipe
            portions: Number of portions

        Returns:
            Cost per portion
        """
        if portions <= 0:
            return Decimal("0")

        return total_cost / Decimal(str(portions))

    @staticmethod
    def calculate_cost_efficiency_score(
        food_cost_percentage: float,
        waste_cost_percentage: float,
        target_food_cost: float = 30.0,
        target_waste_cost: float = 3.0,
    ) -> float:
        """
        Calculate overall cost efficiency score.

        Args:
            food_cost_percentage: Current food cost percentage
            waste_cost_percentage: Current waste cost percentage
            target_food_cost: Target food cost percentage
            target_waste_cost: Target waste cost percentage

        Returns:
            Efficiency score (0-100)
        """
        # Food cost efficiency (70% weight)
        food_cost_score = max(0, 100 - abs(food_cost_percentage - target_food_cost) * 2)

        # Waste cost efficiency (30% weight)
        waste_cost_score = max(
            0, 100 - abs(waste_cost_percentage - target_waste_cost) * 10
        )

        # Weighted average
        return (food_cost_score * 0.7) + (waste_cost_score * 0.3)

    @staticmethod
    def get_cost_status(food_cost_percentage: float) -> str:
        """
        Get cost status based on food cost percentage.

        Args:
            food_cost_percentage: Food cost percentage

        Returns:
            Status: 'excellent', 'good', 'acceptable', 'high', 'critical'
        """
        if food_cost_percentage <= 30:
            return "excellent"
        elif food_cost_percentage <= 35:
            return "good"
        elif food_cost_percentage <= 40:
            return "acceptable"
        elif food_cost_percentage <= 50:
            return "high"
        else:
            return "critical"

    @staticmethod
    def get_waste_status(waste_cost_percentage: float) -> str:
        """
        Get waste status based on waste cost percentage.

        Args:
            waste_cost_percentage: Waste cost percentage

        Returns:
            Status: 'excellent', 'good', 'acceptable', 'high', 'critical'
        """
        if waste_cost_percentage <= 2:
            return "excellent"
        elif waste_cost_percentage <= 3:
            return "good"
        elif waste_cost_percentage <= 5:
            return "acceptable"
        elif waste_cost_percentage <= 10:
            return "high"
        else:
            return "critical"

    @staticmethod
    def grade_performance(score: float) -> str:
        """
        Grade performance based on score.

        Args:
            score: Performance score (0-100)

        Returns:
            Grade: 'A', 'B', 'C', 'D', 'F'
        """
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    @staticmethod
    def format_currency(amount: Decimal, currency: str = "FCFA") -> str:
        """
        Format currency amount for display.

        Args:
            amount: Amount to format
            currency: Currency symbol

        Returns:
            Formatted currency string
        """
        if amount is None:
            return f"0 {currency}"

        # Format with thousand separators
        formatted = f"{amount:,.2f}"
        return f"{formatted} {currency}"

    @staticmethod
    def format_percentage(value: float, decimal_places: int = 1) -> str:
        """
        Format percentage for display.

        Args:
            value: Percentage value
            decimal_places: Number of decimal places

        Returns:
            Formatted percentage string
        """
        return f"{value:.{decimal_places}f}%"

    @staticmethod
    def calculate_cost_trend(
        start_date: date, end_date: date, metric: str = "food_cost_percentage"
    ) -> Dict:
        """
        Calculate cost trend over a date range.

        Args:
            start_date: Start date
            end_date: End date
            metric: Metric to analyze ('food_cost_percentage', 'waste_cost_percentage')

        Returns:
            Trend analysis dictionary
        """
        try:
            summaries = DailySummary.objects.filter(
                date__range=[start_date, end_date]
            ).order_by("date")

            if not summaries.exists():
                return {"error": "No data found for the specified period"}

            # Get daily values
            daily_values = []
            for summary in summaries:
                if metric == "food_cost_percentage":
                    value = summary.food_cost_percentage
                elif metric == "waste_cost_percentage":
                    value = float(
                        (summary.waste_cost / summary.total_sales * 100)
                        if summary.total_sales > 0
                        else 0
                    )
                else:
                    continue

                daily_values.append({"date": summary.date, "value": value})

            if not daily_values:
                return {"error": "No valid data found"}

            # Calculate trend
            first_half = daily_values[: len(daily_values) // 2]
            second_half = daily_values[len(daily_values) // 2 :]

            if not first_half or not second_half:
                return {"trend": "insufficient_data"}

            first_avg = sum(d["value"] for d in first_half) / len(first_half)
            second_avg = sum(d["value"] for d in second_half) / len(second_half)

            if second_avg > first_avg * 1.05:
                trend = "increasing"
            elif second_avg < first_avg * 0.95:
                trend = "decreasing"
            else:
                trend = "stable"

            return {
                "trend": trend,
                "first_half_average": first_avg,
                "second_half_average": second_avg,
                "change_percentage": (
                    ((second_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0
                ),
                "daily_values": daily_values,
            }

        except Exception as e:
            logger.error(f"Error calculating cost trend: {e}")
            return {"error": str(e)}

    @staticmethod
    def generate_cost_alerts(
        start_date: date,
        end_date: date,
        food_cost_threshold: float = 40.0,
        waste_cost_threshold: float = 5.0,
    ) -> List[Dict]:
        """
        Generate cost alerts for a date range.

        Args:
            start_date: Start date
            end_date: End date
            food_cost_threshold: Food cost threshold for alerts
            waste_cost_threshold: Waste cost threshold for alerts

        Returns:
            List of alerts
        """
        alerts = []

        try:
            summaries = DailySummary.objects.filter(
                date__range=[start_date, end_date]
            ).order_by("date")

            for summary in summaries:
                # Food cost alerts
                if summary.food_cost_percentage > food_cost_threshold:
                    alerts.append(
                        {
                            "date": summary.date,
                            "type": "critical",
                            "category": "food_cost",
                            "message": f"Food cost {summary.food_cost_percentage:.1f}% exceeds {food_cost_threshold}% threshold",
                            "value": summary.food_cost_percentage,
                            "threshold": food_cost_threshold,
                        }
                    )
                elif summary.food_cost_percentage > food_cost_threshold - 5:
                    alerts.append(
                        {
                            "date": summary.date,
                            "type": "warning",
                            "category": "food_cost",
                            "message": f"Food cost {summary.food_cost_percentage:.1f}% is elevated",
                            "value": summary.food_cost_percentage,
                            "threshold": food_cost_threshold - 5,
                        }
                    )

                # Waste cost alerts
                waste_percentage = float(
                    (summary.waste_cost / summary.total_sales * 100)
                    if summary.total_sales > 0
                    else 0
                )
                if waste_percentage > waste_cost_threshold:
                    alerts.append(
                        {
                            "date": summary.date,
                            "type": "critical",
                            "category": "waste_cost",
                            "message": f"Waste cost {waste_percentage:.1f}% exceeds {waste_cost_threshold}% threshold",
                            "value": waste_percentage,
                            "threshold": waste_cost_threshold,
                        }
                    )
                elif waste_percentage > waste_cost_threshold - 2:
                    alerts.append(
                        {
                            "date": summary.date,
                            "type": "warning",
                            "category": "waste_cost",
                            "message": f"Waste cost {waste_percentage:.1f}% is elevated",
                            "value": waste_percentage,
                            "threshold": waste_cost_threshold - 2,
                        }
                    )

        except Exception as e:
            logger.error(f"Error generating cost alerts: {e}")
            alerts.append(
                {
                    "date": None,
                    "type": "error",
                    "category": "system",
                    "message": f"Error generating alerts: {str(e)}",
                    "value": None,
                    "threshold": None,
                }
            )

        return alerts

    @staticmethod
    def calculate_cost_variance(
        start_date: date, end_date: date, metric: str = "food_cost_percentage"
    ) -> Dict:
        """
        Calculate cost variance analysis.

        Args:
            start_date: Start date
            end_date: End date
            metric: Metric to analyze

        Returns:
            Variance analysis dictionary
        """
        try:
            summaries = DailySummary.objects.filter(
                date__range=[start_date, end_date]
            ).order_by("date")

            if not summaries.exists():
                return {"error": "No data found for the specified period"}

            # Calculate values
            values = []
            for summary in summaries:
                if metric == "food_cost_percentage":
                    value = summary.food_cost_percentage
                elif metric == "waste_cost_percentage":
                    value = float(
                        (summary.waste_cost / summary.total_sales * 100)
                        if summary.total_sales > 0
                        else 0
                    )
                else:
                    continue

                values.append(value)

            if not values:
                return {"error": "No valid data found"}

            # Calculate statistics
            avg_value = sum(values) / len(values)
            min_value = min(values)
            max_value = max(values)
            variance = max_value - min_value

            # Find high variance days
            high_variance_days = []
            for summary in summaries:
                if metric == "food_cost_percentage":
                    value = summary.food_cost_percentage
                elif metric == "waste_cost_percentage":
                    value = float(
                        (summary.waste_cost / summary.total_sales * 100)
                        if summary.total_sales > 0
                        else 0
                    )
                else:
                    continue

                if abs(value - avg_value) > variance * 0.3:  # 30% of total variance
                    high_variance_days.append(
                        {
                            "date": summary.date,
                            "value": value,
                            "variance": value - avg_value,
                            "reason": "High variance from average",
                        }
                    )

            return {
                "average": avg_value,
                "minimum": min_value,
                "maximum": max_value,
                "variance": variance,
                "high_variance_days": high_variance_days,
                "total_days": len(values),
            }

        except Exception as e:
            logger.error(f"Error calculating cost variance: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_cost_benchmark_comparison(
        food_cost_percentage: float, waste_cost_percentage: float
    ) -> Dict:
        """
        Compare costs to industry benchmarks.

        Args:
            food_cost_percentage: Current food cost percentage
            waste_cost_percentage: Current waste cost percentage

        Returns:
            Benchmark comparison dictionary
        """
        comparisons = {}

        # Food cost comparison
        for level, (min_target, max_target) in CostUtils.COST_BENCHMARKS[
            "food_cost_targets"
        ].items():
            if min_target <= food_cost_percentage <= max_target:
                comparisons["food_cost"] = {
                    "level": level,
                    "current": food_cost_percentage,
                    "target_range": (min_target, max_target),
                    "status": "within_target",
                }
                break
        else:
            # Find closest target
            closest_level = min(
                CostUtils.COST_BENCHMARKS["food_cost_targets"].items(),
                key=lambda x: abs(x[1][0] - food_cost_percentage),
            )
            comparisons["food_cost"] = {
                "level": closest_level[0],
                "current": food_cost_percentage,
                "target_range": closest_level[1],
                "status": "outside_target",
            }

        # Waste cost comparison
        for level, (min_target, max_target) in CostUtils.COST_BENCHMARKS[
            "waste_cost_targets"
        ].items():
            if min_target <= waste_cost_percentage <= max_target:
                comparisons["waste_cost"] = {
                    "level": level,
                    "current": waste_cost_percentage,
                    "target_range": (min_target, max_target),
                    "status": "within_target",
                }
                break
        else:
            # Find closest target
            closest_level = min(
                CostUtils.COST_BENCHMARKS["waste_cost_targets"].items(),
                key=lambda x: abs(x[1][0] - waste_cost_percentage),
            )
            comparisons["waste_cost"] = {
                "level": closest_level[0],
                "current": waste_cost_percentage,
                "target_range": closest_level[1],
                "status": "outside_target",
            }

        return comparisons

    @staticmethod
    def validate_cost_data(
        food_cost: Decimal, revenue: Decimal, waste_cost: Optional[Decimal] = None
    ) -> Dict:
        """
        Validate cost data for consistency.

        Args:
            food_cost: Food cost amount
            revenue: Revenue amount
            waste_cost: Waste cost amount (optional)

        Returns:
            Validation results dictionary
        """
        validation_results = {"is_valid": True, "warnings": [], "errors": []}

        # Check for negative values
        if food_cost < 0:
            validation_results["errors"].append("Food cost cannot be negative")
            validation_results["is_valid"] = False

        if revenue < 0:
            validation_results["errors"].append("Revenue cannot be negative")
            validation_results["is_valid"] = False

        if waste_cost is not None and waste_cost < 0:
            validation_results["errors"].append("Waste cost cannot be negative")
            validation_results["is_valid"] = False

        # Check for zero revenue
        if revenue == 0:
            validation_results["warnings"].append(
                "Revenue is zero - cost percentages will be zero"
            )

        # Check for excessive food cost
        if revenue > 0:
            food_cost_percentage = float((food_cost / revenue) * 100)
            if food_cost_percentage > 100:
                validation_results["errors"].append("Food cost exceeds revenue")
                validation_results["is_valid"] = False
            elif food_cost_percentage > 80:
                validation_results["warnings"].append(
                    "Food cost is extremely high (>80%)"
                )

        # Check for excessive waste cost
        if waste_cost is not None and revenue > 0:
            waste_cost_percentage = float((waste_cost / revenue) * 100)
            if waste_cost_percentage > 50:
                validation_results["warnings"].append(
                    "Waste cost is extremely high (>50%)"
                )

        return validation_results

    @staticmethod
    def get_cost_summary_stats(start_date: date, end_date: date) -> Dict:
        """
        Get summary statistics for cost analysis.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Summary statistics dictionary
        """
        try:
            summaries = DailySummary.objects.filter(date__range=[start_date, end_date])

            if not summaries.exists():
                return {"error": "No data found for the specified period"}

            # Calculate totals
            total_food_cost = summaries.aggregate(total=Sum("total_food_cost"))[
                "total"
            ] or Decimal("0")
            total_revenue = summaries.aggregate(total=Sum("total_sales"))[
                "total"
            ] or Decimal("0")
            total_waste_cost = summaries.aggregate(total=Sum("waste_cost"))[
                "total"
            ] or Decimal("0")

            # Calculate averages
            avg_food_cost_percentage = (
                summaries.aggregate(avg=Avg("food_cost_percentage"))["avg"] or 0
            )
            avg_daily_revenue = (
                total_revenue / summaries.count()
                if summaries.count() > 0
                else Decimal("0")
            )
            avg_daily_food_cost = (
                total_food_cost / summaries.count()
                if summaries.count() > 0
                else Decimal("0")
            )

            # Calculate waste percentage
            waste_cost_percentage = float(
                (total_waste_cost / total_revenue * 100) if total_revenue > 0 else 0
            )

            return {
                "period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "days_count": summaries.count(),
                },
                "totals": {
                    "total_food_cost": total_food_cost,
                    "total_revenue": total_revenue,
                    "total_waste_cost": total_waste_cost,
                    "gross_profit": total_revenue - total_food_cost - total_waste_cost,
                },
                "averages": {
                    "avg_food_cost_percentage": avg_food_cost_percentage,
                    "avg_daily_revenue": avg_daily_revenue,
                    "avg_daily_food_cost": avg_daily_food_cost,
                    "waste_cost_percentage": waste_cost_percentage,
                },
                "performance": {
                    "food_cost_status": CostUtils.get_cost_status(
                        avg_food_cost_percentage
                    ),
                    "waste_status": CostUtils.get_waste_status(waste_cost_percentage),
                    "efficiency_score": CostUtils.calculate_cost_efficiency_score(
                        avg_food_cost_percentage, waste_cost_percentage
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Error getting cost summary stats: {e}")
            return {"error": str(e)}

import json
import logging
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from apps.analytics.models import DailySummary

from .services.revenue_analytics import RevenueAnalyticsService
from .services.services import DailyAnalyticsService

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal objects"""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class AnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    """
    Server-Side Rendered Dashboard with Chapter Structure.

    Features:
    - All data rendered server-side (no AJAX needed)
    - Maintains chapter structure from dashboard_unified.html
    - Aggressive caching for performance
    - Progressive enhancement with minimal JavaScript
    """

    template_name = "analytics/dashboard_unified.html"

    @method_decorator(cache_page(300))  # Cache for 5 minutes
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get date range from request or default to last 7 days
        selected_days = int(self.request.GET.get("days", 7))

        # Get chapter from request or default to morning insights
        selected_chapter = self.request.GET.get("chapter", "morning")

        # Enhanced cache key with more granularity for SSR
        user_id = self.request.user.id
        # Include latest available DailySummary date to ensure analysis is aligned with last data
        try:
            latest_summary = DailySummary.objects.order_by("-date").only("date").first()
            latest_date_str = (
                latest_summary.date.isoformat()
                if latest_summary
                else date.today().isoformat()
            )
        except Exception:
            latest_date_str = date.today().isoformat()
        # Add version identifier to force cache refresh after fixes
        cache_key = f"dashboard_ssr_v2_{selected_days}_{selected_chapter}_{user_id}_{latest_date_str}"

        try:
            dashboard_data = cache.get(cache_key)
        except Exception as e:
            logger.warning(f"Failed to get cache: {e}")
            dashboard_data = None

        if not dashboard_data:
            dashboard_data = self._generate_dashboard_data(selected_days)
            # Cache for 5 minutes with user-specific data
            try:
                cache.set(cache_key, dashboard_data, 300)
            except Exception as e:
                logger.warning(f"Failed to set cache: {e}")

        context.update(dashboard_data)
        context["selected_chapter"] = selected_chapter
        return context

    def _generate_dashboard_data(self, selected_days):
        """Generate all dashboard data server-side with chapter structure"""
        try:
            # Get date range: use the latest available sales date (DailySummary)
            latest_summary = DailySummary.objects.order_by("-date").only("date").first()
            if latest_summary:
                end_date = latest_summary.date
            else:
                end_date = date.today() - timedelta(days=1)

            # Calculate start date to get exactly selected_days of data
            # For 7 days ending on end_date, we need 7 days total
            start_date = end_date - timedelta(days=selected_days - 1)

            # Ensure we don't go beyond available data
            earliest_summary = (
                DailySummary.objects.order_by("date").only("date").first()
            )
            if earliest_summary and start_date < earliest_summary.date:
                start_date = earliest_summary.date
                # Recalculate end_date to maintain the selected_days period
                end_date = start_date + timedelta(days=selected_days - 1)
                # But don't exceed the latest available data
                if end_date > latest_summary.date:
                    end_date = latest_summary.date

            # Get comprehensive data for all chapters with SSR optimizations
            data = self._get_chapter_data(start_date, end_date, selected_days)

            # Keep Decimal values for precision (SSR handles formatting)
            return data

        except Exception as e:
            logger.error(f"Error generating unified dashboard data: {e}")
            return {"error": str(e)}

    def _get_chapter_data(self, start_date, end_date, selected_days):
        """Get data for all dashboard chapters with SSR optimizations"""
        revenue_service = RevenueAnalyticsService()

        # Get all analytics data in one go for SSR optimization
        revenue_overview = revenue_service.get_revenue_overview(start_date, end_date)
        top_categories = revenue_service.get_top_performing_categories(
            start_date, end_date
        )
        day_of_week_data = revenue_service.get_day_of_week_revenue(start_date, end_date)
        payment_analysis = revenue_service.get_payment_method_analysis(
            start_date, end_date
        )
        top_products = revenue_service.get_top_performing_products(start_date, end_date)

        # Chapter 1: Morning Insights data
        morning_data = self._get_morning_chapter_data(
            start_date, end_date, selected_days
        )

        # Chapter 2: Revenue Story data
        revenue_chapter_data = self._get_revenue_chapter_data(
            start_date,
            end_date,
            revenue_overview,
            top_categories,
            day_of_week_data,
            payment_analysis,
            top_products,
        )

        # Chapter 3: Cost Chronicles data
        cost_data = self._get_cost_chapter_data(start_date, end_date)

        # Chapter 4: Recipe Mastery data (placeholder)
        recipe_data = self._get_recipe_chapter_data(start_date, end_date)

        # Chapter 5: Performance Excellence data
        performance_data = self._get_performance_chapter_data(start_date, end_date)

        # Generate SSR-specific insights
        insights = self._generate_server_side_insights(
            revenue_overview,
            top_categories,
            day_of_week_data,
            payment_analysis,
            selected_days,
        )

        # Pre-calculate chart data server-side
        chart_data = self._pre_calculate_chart_data(
            revenue_overview,
            top_categories,
            day_of_week_data,
            payment_analysis,
            top_products,
        )

        # Calculate performance metrics server-side
        performance_metrics = self._calculate_performance_metrics(revenue_overview)

        # Get daily summaries for revenue data
        recent_summaries = DailySummary.objects.filter(
            date__range=[start_date, end_date]
        ).order_by("date")

        # Prepare simple data structures for charts
        # Generate complete date range with sales data (including zero sales days)
        chart_dates = []
        chart_revenues = []
        current_date = start_date

        while current_date <= end_date:
            chart_dates.append(current_date.strftime("%d/%m"))

            # Find sales data for this date
            summary = next(
                (s for s in recent_summaries if s.date == current_date), None
            )
            if summary:
                chart_revenues.append(float(summary.total_sales or 0))
            else:
                chart_revenues.append(0.0)

            current_date += timedelta(days=1)

        simple_revenue_data = {
            "revenue": chart_revenues,
            "labels": chart_dates,
        }

        if top_categories.get("categories"):
            category_data = {
                "revenue": [
                    float(cat.get("total_revenue", 0))
                    for cat in top_categories.get("categories", [])
                ],
                "labels": [
                    cat.get("category_name", "Unknown")
                    for cat in top_categories.get("categories", [])
                ],
            }
        else:
            category_data = {
                "revenue": [],
                "labels": [],
            }

        # Provide latest summary (previously referenced as 'yesterday' in templates)
        latest_summary = DailySummary.objects.filter(date=end_date).first()

        return {
            "selected_days": selected_days,
            "date_range": {
                "start": start_date,
                "end": end_date,
                "start_formatted": start_date.strftime("%Y-%m-%d"),
                "end_formatted": end_date.strftime("%Y-%m-%d"),
            },
            # Chapter data
            "morning_data": morning_data,
            "revenue_data": revenue_chapter_data,
            "cost_data": cost_data,
            "recipe_data": recipe_data,
            "performance_data": performance_data,
            # Backward-compatible variable used in template alerts
            "yesterday": latest_summary,
            # Cost data for Chapter 3 (Cost Chronicles) - pass at top level
            "cost_analytics": cost_data.get("cost_analytics", {}),
            "cost_metrics": cost_data.get("cost_metrics", {}),
            # SSR optimizations
            "ssr_optimized": True,
            "insights": insights,
            "chart_data": chart_data,
            "performance_metrics": performance_metrics,
            "revenue_overview": revenue_overview,
            "top_categories": top_categories,
            "day_of_week_data": day_of_week_data,
            "payment_analysis": payment_analysis,
            "top_products": (
                top_products.get("products", [])
                if isinstance(top_products, dict)
                else top_products
            ),
            # Chart data for JavaScript (converted to JSON strings)
            "revenue_chart_data": json.dumps(simple_revenue_data, cls=DecimalEncoder),
            "category_data": json.dumps(category_data, cls=DecimalEncoder),
            # Revenue data for Chapter 2 (Revenue Story)
            "revenue_data": revenue_chapter_data,
            # Chart data for Chapter 2 (Revenue Story) - use the chart data from revenue chapter
            "daily_revenue_chart": revenue_chapter_data.get("daily_revenue_chart", ""),
            "time_based_chart": revenue_chapter_data.get("time_based_chart", ""),
            "payment_chart": revenue_chapter_data.get("payment_chart", ""),
            "product_chart": revenue_chapter_data.get("product_chart", ""),
            "revenue_category_chart": revenue_chapter_data.get(
                "revenue_category_chart", ""
            ),
        }

    def _get_morning_chapter_data(self, start_date, end_date, selected_days):
        """Get data for Morning Insights chapter"""
        from django.db.models import Avg, Sum

        # Get daily summaries for the period
        recent_summaries = DailySummary.objects.filter(
            date__range=[start_date, end_date]
        ).order_by("date")

        # Calculate period totals
        period_totals = recent_summaries.aggregate(
            total_sales=Sum("total_sales"),
            total_orders=Sum("total_orders"),
            total_customers=Sum("total_customers"),
            registered_customers=Sum("registered_customers"),
            walk_in_customers=Sum("walk_in_customers"),
            avg_food_cost_pct=Avg("food_cost_percentage"),
            total_food_cost=Sum("total_food_cost"),
        )

        # Add accurate period-total based food cost percentage as a separate field
        try:
            from decimal import Decimal

            sum_food_cost = period_totals.get("total_food_cost") or Decimal("0")
            sum_sales_for_cost = period_totals.get("total_sales") or Decimal("0")
            if sum_sales_for_cost and sum_sales_for_cost > 0:
                period_food_cost_pct = (sum_food_cost / sum_sales_for_cost) * Decimal(
                    "100"
                )
            else:
                period_food_cost_pct = Decimal("0")
            period_totals["period_food_cost_pct"] = period_food_cost_pct
        except Exception:
            # If anything goes wrong, omit the field; template will fall back
            period_totals["period_food_cost_pct"] = None

        # Calculate previous period for comparison
        prev_start = start_date - timedelta(days=selected_days)
        prev_end = start_date - timedelta(days=1)
        prev_summaries = DailySummary.objects.filter(date__range=[prev_start, prev_end])
        prev_totals = prev_summaries.aggregate(
            total_sales=Sum("total_sales"),
            total_orders=Sum("total_orders"),
            total_customers=Sum("total_customers"),
        )

        # Calculate percentage changes
        def calc_change(current, previous):
            if previous and previous > 0:
                return ((current or 0) - previous) / previous * 100
            return 0

        sales_change = calc_change(
            period_totals.get("total_sales"), prev_totals.get("total_sales")
        )
        orders_change = calc_change(
            period_totals.get("total_orders"), prev_totals.get("total_orders")
        )
        customers_change = calc_change(
            period_totals.get("total_customers"), prev_totals.get("total_customers")
        )

        # Prepare revenue trends
        revenue_trends = []
        max_sales = 0
        if recent_summaries:
            max_sales = max(
                float(summary.total_sales or 0) for summary in recent_summaries
            )

        for summary in recent_summaries:
            sales = float(summary.total_sales or 0)
            percentage = (sales / max_sales * 100) if max_sales > 0 else 0
            revenue_trends.append(
                {
                    "date": summary.date.strftime("%Y-%m-%d"),
                    "sales": sales,
                    "percentage": percentage,
                    "orders": summary.total_orders or 0,
                    "customers": summary.total_customers or 0,
                }
            )

        return {
            "week_totals": period_totals,
            "sales_change": sales_change,
            "orders_change": orders_change,
            "customers_change": customers_change,
            "revenue_trends": revenue_trends,
            "daily_data": list(
                recent_summaries.values(
                    "date", "total_sales", "total_orders", "total_customers"
                )
            ),
        }

    def _get_revenue_chapter_data(
        self,
        start_date,
        end_date,
        revenue_overview,
        top_categories,
        day_of_week_data,
        payment_analysis,
        top_products,
    ):
        """Get data for Revenue Story chapter"""
        revenue_service = RevenueAnalyticsService()

        # Get revenue insights (revenue_overview is already provided)
        revenue_insights = revenue_service.get_revenue_insights(start_date, end_date)

        # Import and use utility functions for chart data
        from apps.analytics.utils.revenue_utils import RevenueChartUtils

        chart_utils = RevenueChartUtils()

        # Get properly formatted chart data
        daily_revenue_chart_data = chart_utils.prepare_daily_revenue_chart_data(
            start_date, end_date
        )
        payment_chart_data = chart_utils.prepare_payment_method_chart_data(
            start_date, end_date
        )

        # Convert chart data to JSON strings for template
        daily_revenue_chart_json = {
            "labels": (
                daily_revenue_chart_data.get("data", {}).get("labels", [])
                if not daily_revenue_chart_data.get("error")
                else []
            ),
            "revenue": (
                daily_revenue_chart_data.get("data", {})
                .get("datasets", [{}])[0]
                .get("data", [])
                if daily_revenue_chart_data.get("data", {}).get("datasets")
                and not daily_revenue_chart_data.get("error")
                else []
            ),
        }

        payment_chart_json = {
            "labels": (
                ["Cash", "Mobile Money", "Card", "Other"]
                if not payment_chart_data.get("error")
                else []
            ),
            "amounts": (
                payment_chart_data.get("data", {})
                .get("datasets", [{}])[0]
                .get("data", [])
                if payment_chart_data.get("data", {}).get("datasets")
                and not payment_chart_data.get("error")
                else []
            ),
        }

        product_chart_json = {
            "labels": [
                product.get("product_name", "Unknown")
                for product in top_products.get("products", [])
            ],
            "revenue": [
                float(product.get("total_revenue", 0))
                for product in top_products.get("products", [])
            ],
        }

        time_based_chart_json = {
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
            "revenue": day_of_week_data.get("revenue", [0, 0, 0, 0, 0, 0, 0]),
        }

        revenue_category_chart_json = {
            "labels": [
                cat.get("category_name", "Unknown")
                for cat in top_categories.get("categories", [])
            ],
            "revenue": [
                float(cat.get("total_revenue", 0))
                for cat in top_categories.get("categories", [])
            ],
        }

        return {
            "revenue_overview": revenue_overview,
            "top_categories": top_categories,
            "revenue_insights": revenue_insights,
            "day_of_week_data": day_of_week_data,
            "payment_analysis": payment_analysis,
            "top_products": (
                top_products.get("products", [])
                if isinstance(top_products, dict)
                else top_products
            ),
            "daily_revenue_chart": json.dumps(
                daily_revenue_chart_json, cls=DecimalEncoder
            ),
            "payment_chart": json.dumps(payment_chart_json, cls=DecimalEncoder),
            "product_chart": json.dumps(product_chart_json, cls=DecimalEncoder),
            "time_based_chart": json.dumps(time_based_chart_json, cls=DecimalEncoder),
            "revenue_category_chart": json.dumps(
                revenue_category_chart_json, cls=DecimalEncoder
            ),
        }

    def _get_cost_chapter_data(self, start_date, end_date):
        """Get data for Cost Chronicles chapter"""
        from .services.cost_analytics import CostAnalyticsService

        cost_service = CostAnalyticsService()
        cost_analytics_data = cost_service.get_cost_analytics_data(start_date, end_date)

        cost_analytics = cost_analytics_data.get("cost_analytics", {})

        return {
            "cost_analytics": cost_analytics,
            "cost_metrics": cost_analytics_data.get("cost_metrics", {}),
        }

    def _get_recipe_chapter_data(self, start_date, end_date):
        """Get data for Recipe Mastery chapter (placeholder)"""
        # TODO: Implement recipe analytics when available
        return {
            "recipes": [],
            "recipe_insights": [],
        }

    def _get_performance_chapter_data(self, start_date, end_date):
        """Get data for Performance Excellence chapter"""
        service = DailyAnalyticsService()
        target_date = end_date

        # Get performance analysis
        performance_data = service.get_performance_analysis(target_date)
        payment_analysis = service.get_payment_method_analysis(start_date, end_date)

        # Get monthly performance report
        current_month = target_date.month
        current_year = target_date.year
        monthly_report = service.get_monthly_performance_report(
            current_year, current_month
        )

        # Add SSR-specific performance insights
        performance_insights = self._generate_performance_insights(
            performance_data, payment_analysis, monthly_report
        )

        return {
            "performance_data": performance_data,
            "payment_analysis": payment_analysis,
            "monthly_report": monthly_report,
            "target_date": target_date,
            "performance_insights": performance_insights,
        }

    def _generate_server_side_insights(
        self,
        revenue_overview,
        top_categories,
        day_of_week_data,
        payment_analysis,
        selected_days,
    ):
        """Generate insights server-side to reduce client-side processing"""
        insights = {
            "revenue_performance": [],
            "category_insights": [],
            "time_insights": [],
            "payment_insights": [],
            "recommendations": [],
        }

        # Revenue performance insights
        if revenue_overview.get("total_metrics", {}).get("total_revenue", 0) > 0:
            # Calculate average daily revenue based on selected period
            period_days = max(selected_days, 1)  # Ensure we don't divide by zero
            avg_daily = revenue_overview["total_metrics"]["total_revenue"] / period_days
            if avg_daily > 300000:
                insights["revenue_performance"].append(
                    "Excellent daily revenue performance"
                )
            elif avg_daily > 150000:
                insights["revenue_performance"].append("Good revenue performance")
            else:
                insights["revenue_performance"].append("Revenue needs improvement")

        # Category insights
        if top_categories.get("categories"):
            top_category = top_categories["categories"][0]
            insights["category_insights"].append(
                f"{top_category['category_name']} is your best performing category"
            )

        # Time insights
        if day_of_week_data.get("daily_revenue"):
            best_day = max(
                day_of_week_data["daily_revenue"], key=lambda x: x["revenue"]
            )
            insights["time_insights"].append(
                f"{best_day['day_name']} is your best performing day"
            )

        # Payment insights
        if payment_analysis.get("payment_methods"):
            cash_percentage = next(
                (
                    pm["percentage"]
                    for pm in payment_analysis["payment_methods"]
                    if pm["method"] == "Cash"
                ),
                0,
            )
            if cash_percentage > 80:
                insights["payment_insights"].append(
                    "High cash dependency - consider digital payments"
                )

        # Recommendations
        insights["recommendations"] = [
            {
                "category": "Revenue",
                "action": "Focus on top-performing categories",
                "impact": "Increase revenue by 15-20%",
                "priority": "high",
            },
            {
                "category": "Operations",
                "action": "Optimize staffing for peak days",
                "impact": "Improve customer service",
                "priority": "medium",
            },
        ]

        return insights

    def _convert_decimals_in_dict(self, data):
        """Recursively convert Decimal values to float in dictionaries for JSON serialization"""
        if isinstance(data, dict):
            for key, value in data.items():
                if hasattr(value, "as_tuple"):  # Check if it's a Decimal
                    data[key] = float(value)
                elif isinstance(value, dict):
                    self._convert_decimals_in_dict(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            self._convert_decimals_in_dict(item)
                        elif hasattr(item, "as_tuple"):  # Check if list item is Decimal
                            item = float(item)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    self._convert_decimals_in_dict(item)
                elif hasattr(item, "as_tuple"):  # Check if list item is Decimal
                    data[i] = float(item)
        return data

    def _pre_calculate_chart_data(
        self,
        revenue_overview,
        top_categories,
        day_of_week_data,
        payment_analysis,
        top_products,
    ):
        """Pre-calculate all chart data server-side"""
        chart_data = {
            "daily_revenue": {
                "labels": [
                    item["date"] for item in revenue_overview.get("daily_revenue", [])
                ],
                "data": [
                    float(item["revenue"])
                    for item in revenue_overview.get("daily_revenue", [])
                ],
            },
            "category_chart": {
                "labels": [
                    cat["category_name"] for cat in top_categories.get("categories", [])
                ],
                "data": [
                    float(cat["total_revenue"])
                    for cat in top_categories.get("categories", [])
                ],
            },
            "day_of_week": {
                "labels": [
                    item["day_name"]
                    for item in day_of_week_data.get("daily_revenue", [])
                ],
                "data": [
                    float(item["revenue"])
                    for item in day_of_week_data.get("daily_revenue", [])
                ],
            },
            "payment_methods": {
                "labels": [
                    pm["method"] for pm in payment_analysis.get("payment_methods", [])
                ],
                "data": [
                    float(pm["amount"])
                    for pm in payment_analysis.get("payment_methods", [])
                ],
            },
            "top_products": {
                "labels": [
                    prod["product_name"] for prod in top_products.get("products", [])
                ],
                "data": [
                    float(prod["total_revenue"])
                    for prod in top_products.get("products", [])
                ],
            },
        }

        # Convert any remaining Decimal values to float for JSON serialization
        return self._convert_decimals_in_dict(chart_data)

    def _calculate_performance_metrics(self, revenue_overview):
        """Calculate performance metrics server-side"""
        total_revenue = revenue_overview.get("total_metrics", {}).get(
            "total_revenue", 0
        )
        total_orders = revenue_overview.get("total_metrics", {}).get("total_orders", 0)
        total_customers = revenue_overview.get("total_metrics", {}).get(
            "total_customers", 0
        )

        return {
            "avg_order_value": total_revenue / total_orders if total_orders > 0 else 0,
            "avg_ticket_size": (
                total_revenue / total_customers if total_customers > 0 else 0
            ),
            "orders_per_customer": (
                total_orders / total_customers if total_customers > 0 else 0
            ),
            "revenue_per_customer": (
                total_revenue / total_customers if total_customers > 0 else 0
            ),
        }

    def _generate_performance_insights(
        self, performance_data, payment_analysis, monthly_report
    ):
        """Generate performance insights server-side"""
        insights = {
            "operational_insights": [],
            "financial_insights": [],
            "customer_insights": [],
            "action_items": [],
        }

        # Operational insights
        if performance_data.get("daily_performance"):
            daily_perf = performance_data["daily_performance"]
            if daily_perf.get("efficiency_score", 0) > 80:
                insights["operational_insights"].append(
                    "Excellent operational efficiency"
                )
            elif daily_perf.get("efficiency_score", 0) > 60:
                insights["operational_insights"].append("Good operational performance")
            else:
                insights["operational_insights"].append(
                    "Operational efficiency needs improvement"
                )

        # Financial insights
        if monthly_report.get("revenue_growth"):
            growth = monthly_report["revenue_growth"]
            if growth > 10:
                insights["financial_insights"].append("Strong revenue growth trend")
            elif growth > 0:
                insights["financial_insights"].append("Moderate revenue growth")
            else:
                insights["financial_insights"].append("Revenue growth needs attention")

        # Customer insights
        if performance_data.get("customer_metrics"):
            customer_metrics = performance_data["customer_metrics"]
            if customer_metrics.get("satisfaction_score", 0) > 4.0:
                insights["customer_insights"].append("High customer satisfaction")
            elif customer_metrics.get("satisfaction_score", 0) > 3.0:
                insights["customer_insights"].append("Good customer satisfaction")
            else:
                insights["customer_insights"].append(
                    "Customer satisfaction needs improvement"
                )

        # Action items
        insights["action_items"] = [
            {
                "priority": "high",
                "action": "Review peak hour staffing",
                "impact": "Improve customer service during busy periods",
            },
            {
                "priority": "medium",
                "action": "Analyze payment method preferences",
                "impact": "Optimize payment processing",
            },
        ]

        return insights


@require_http_methods(["GET"])
def performance_monitor_api(request):
    """API endpoint for monitoring SSR performance"""
    try:
        user_id = request.user.id if request.user.is_authenticated else "anonymous"

        # Get performance data from cache
        performance_data = {}
        cache_keys = [
            f"ssr_performance_/_{user_id}",
            f"ssr_performance_/analytics/_{user_id}",
        ]

        for key in cache_keys:
            duration = cache.get(key)
            if duration:
                path = key.replace("ssr_performance_", "").replace(f"_{user_id}", "")
                performance_data[path] = {
                    "duration": duration,
                    "status": (
                        "fast"
                        if duration < 1.0
                        else "slow" if duration > 3.0 else "normal"
                    ),
                }

        return JsonResponse(
            {
                "performance": performance_data,
                "timestamp": date.today().isoformat(),
                "user_id": user_id,
            }
        )

    except Exception as e:
        logger.error(f"Error in performance monitor API: {e}")
        return JsonResponse({"error": str(e)}, status=500)

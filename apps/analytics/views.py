from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum
from django.shortcuts import render
from django.utils.translation import gettext as _

from apps.analytics.models import DailySummary

from .services.services import DailyAnalyticsService


@login_required
def analytics_dashboard(request):
    """Main analytics dashboard"""

    service = DailyAnalyticsService()

    # Get recent summaries (last 7 days)
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=6)

    recent_summaries = DailySummary.objects.filter(
        date__range=[start_date, end_date]
    ).order_by("date")

    # Calculate totals for the week
    week_totals = recent_summaries.aggregate(
        total_sales=Sum("total_sales"),
        total_orders=Sum("total_orders"),
        avg_food_cost_pct=Avg("food_cost_percentage"),
    )

    # Get yesterday's performance
    yesterday = DailySummary.objects.filter(date=end_date).first()

    # Get top products for yesterday
    top_products = []
    if yesterday:
        top_products = service.get_sales_by_product(end_date)[:5]

    context = {
        "title": _("Analytics Dashboard"),
        "recent_summaries": recent_summaries,
        "week_totals": week_totals,
        "yesterday": yesterday,
        "top_products": top_products,
        "date_range": {"start": start_date, "end": end_date},
    }

    return render(request, "analytics/dashboard.html", context)


@login_required
def analytics_dashboard_african(request):
    """African-inspired analytics dashboard with modern design"""

    service = DailyAnalyticsService()

    # Get recent summaries (last 7 days)
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=6)

    recent_summaries = DailySummary.objects.filter(
        date__range=[start_date, end_date]
    ).order_by("date")

    # Calculate totals for the week
    week_totals = recent_summaries.aggregate(
        total_sales=Sum("total_sales"),
        total_orders=Sum("total_orders"),
        avg_food_cost_pct=Avg("food_cost_percentage"),
    )

    # Get yesterday's performance
    yesterday = DailySummary.objects.filter(date=end_date).first()

    # Get top products for yesterday
    top_products = []
    if yesterday:
        top_products = service.get_sales_by_product(end_date)[:5]

    context = {
        "title": _("Restaurant Analytics Dashboard"),
        "recent_summaries": recent_summaries,
        "week_totals": week_totals,
        "yesterday": yesterday,
        "top_products": top_products,
        "date_range": {"start": start_date, "end": end_date},
    }

    return render(request, "analytics/dashboard_african.html", context)


@login_required
def analytics_dashboard_unified(request):
    """Unified story-driven analytics dashboard with African design"""

    service = DailyAnalyticsService()

    # Get recent summaries (last 7 days)
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=6)

    recent_summaries = DailySummary.objects.filter(
        date__range=[start_date, end_date]
    ).order_by("date")

    # Calculate totals for the week
    week_totals = recent_summaries.aggregate(
        total_sales=Sum("total_sales"),
        total_orders=Sum("total_orders"),
        avg_food_cost_pct=Avg("food_cost_percentage"),
    )

    # Get yesterday's performance
    yesterday = DailySummary.objects.filter(date=end_date).first()

    # Get top products for yesterday
    top_products = []
    if yesterday:
        top_products = service.get_sales_by_product(end_date)[:5]

    # Calculate week-over-week changes
    previous_week_start = start_date - timedelta(days=7)
    previous_week_end = start_date - timedelta(days=1)

    previous_week_summaries = DailySummary.objects.filter(
        date__range=[previous_week_start, previous_week_end]
    )

    previous_week_totals = previous_week_summaries.aggregate(
        total_sales=Sum("total_sales"),
        total_orders=Sum("total_orders"),
    )

    # Calculate percentage changes
    sales_change = 0
    orders_change = 0

    if previous_week_totals["total_sales"] and previous_week_totals["total_sales"] > 0:
        sales_change = (
            ((week_totals["total_sales"] or 0) - previous_week_totals["total_sales"])
            / previous_week_totals["total_sales"]
            * 100
        )

    if (
        previous_week_totals["total_orders"]
        and previous_week_totals["total_orders"] > 0
    ):
        orders_change = (
            ((week_totals["total_orders"] or 0) - previous_week_totals["total_orders"])
            / previous_week_totals["total_orders"]
            * 100
        )

    context = {
        "title": _("Your Restaurant Story"),
        "recent_summaries": recent_summaries,
        "week_totals": week_totals,
        "yesterday": yesterday,
        "top_products": top_products,
        "date_range": {"start": start_date, "end": end_date},
        "sales_change": sales_change,
        "orders_change": orders_change,
    }

    return render(request, "analytics/dashboard_unified.html", context)


@login_required
def sales_analytics(request):
    """Sales analytics view"""

    # Get last 30 days
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=29)

    daily_summaries = DailySummary.objects.filter(
        date__range=[start_date, end_date]
    ).order_by("date")

    # Calculate monthly totals
    monthly_totals = daily_summaries.aggregate(
        total_sales=Sum("total_sales"),
        total_orders=Sum("total_orders"),
        total_customers=Sum("total_customers"),
        avg_order_value=Avg("average_order_value"),
    )

    context = {
        "title": _("Sales Analytics"),
        "daily_summaries": daily_summaries,
        "monthly_totals": monthly_totals,
        "chart_data": list(
            daily_summaries.values("date", "total_sales", "total_orders")
        ),
    }

    return render(request, "analytics/sales.html", context)


@login_required
def cost_analytics(request):
    """Cost analytics view"""

    # Get last 30 days
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=29)

    daily_summaries = DailySummary.objects.filter(
        date__range=[start_date, end_date]
    ).order_by("date")

    # Calculate cost metrics
    cost_totals = daily_summaries.aggregate(
        total_food_cost=Sum("total_food_cost"),
        avg_food_cost_pct=Avg("food_cost_percentage"),
        total_gross_profit=Sum("gross_profit"),
    )

    context = {
        "title": _("Cost Analytics"),
        "daily_summaries": daily_summaries,
        "cost_totals": cost_totals,
        "chart_data": list(
            daily_summaries.values("date", "food_cost_percentage", "gross_profit")
        ),
    }

    return render(request, "analytics/costs.html", context)


@login_required
def performance_analysis(request):
    """Enhanced performance analysis with grading and insights"""

    service = DailyAnalyticsService()

    # Get target date from request or default to yesterday
    target_date_str = request.GET.get("date")
    if target_date_str:
        try:
            target_date = date.fromisoformat(target_date_str)
        except ValueError:
            target_date = date.today() - timedelta(days=1)
    else:
        target_date = date.today() - timedelta(days=1)

    # Get performance analysis
    performance_data = service.get_performance_analysis(target_date)

    # Get payment method analysis for last 30 days
    end_date = target_date
    start_date = end_date - timedelta(days=29)
    payment_analysis = service.get_payment_method_analysis(start_date, end_date)

    # Get monthly performance report
    current_month = target_date.month
    current_year = target_date.year
    monthly_report = service.get_monthly_performance_report(current_year, current_month)

    # Get recent daily summaries for trend analysis
    recent_summaries = DailySummary.objects.filter(
        date__range=[start_date, end_date]
    ).order_by("date")

    context = {
        "title": _("Performance Analysis"),
        "target_date": target_date,
        "performance_data": performance_data,
        "payment_analysis": payment_analysis,
        "monthly_report": monthly_report,
        "recent_summaries": recent_summaries,
        "service": service,  # Pass service for template access to benchmarks
    }

    return render(request, "analytics/performance.html", context)


@login_required
def payment_analytics(request):
    """Payment method analytics view"""

    service = DailyAnalyticsService()

    # Get last 30 days
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=29)

    payment_analysis = service.get_payment_method_analysis(start_date, end_date)

    # Get daily payment trends
    daily_summaries = DailySummary.objects.filter(
        date__range=[start_date, end_date]
    ).order_by("date")

    context = {
        "title": _("Payment Analytics"),
        "payment_analysis": payment_analysis,
        "daily_summaries": daily_summaries,
        "service": service,
    }

    return render(request, "analytics/payments.html", context)


@login_required
def recipe_costing_analysis(request):
    """Recipe costing analysis view"""

    service = DailyAnalyticsService()

    # Get target date from request or default to yesterday
    target_date_str = request.GET.get("date")
    if target_date_str:
        try:
            target_date = date.fromisoformat(target_date_str)
        except ValueError:
            target_date = date.today() - timedelta(days=1)
    else:
        target_date = date.today() - timedelta(days=1)

    # Get recipe cost analysis
    recipe_analysis = service.get_recipe_cost_analysis(target_date)

    # Get cost efficiency analysis
    efficiency_analysis = service.get_cost_efficiency_analysis()

    # Get ingredient cost trends
    ingredient_trends = service.get_product_cost_trends(days=30)

    context = {
        "title": _("Recipe Costing Analysis"),
        "target_date": target_date,
        "recipe_analysis": recipe_analysis,
        "efficiency_analysis": efficiency_analysis,
        "ingredient_trends": ingredient_trends,
    }

    return render(request, "analytics/recipe_costing.html", context)


@login_required
def ingredient_cost_trends(request):
    service = DailyAnalyticsService()
    days = int(request.GET.get("days", 30))
    product_trends = service.get_product_cost_trends(days=days)
    context = {
        "title": _("Product Cost Trends"),
        "days": days,
        "product_trends": product_trends,
    }
    return render(request, "analytics/ingredient_cost_trends.html", context)


@login_required
def cost_efficiency_analysis(request):
    """Cost efficiency analysis view"""

    service = DailyAnalyticsService()

    # Get cost efficiency analysis
    efficiency_analysis = service.get_cost_efficiency_analysis()

    # Get recipe cost analysis for today
    recipe_analysis = service.get_recipe_cost_analysis()

    context = {
        "title": _("Cost Efficiency Analysis"),
        "efficiency_analysis": efficiency_analysis,
        "recipe_analysis": recipe_analysis,
    }

    return render(request, "analytics/cost_efficiency.html", context)

from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    # Main dashboard - now points to unified version
    path("", views.analytics_dashboard_unified, name="dashboard"),
    path("unified/", views.analytics_dashboard_unified, name="dashboard_unified"),
    # Legacy dashboards (for comparison)
    path("classic/", views.analytics_dashboard, name="dashboard_classic"),
    path("african/", views.analytics_dashboard_african, name="dashboard_african"),
    # Specific analytics
    path("sales/", views.sales_analytics, name="sales"),
    path("costs/", views.cost_analytics, name="costs"),
    path("performance/", views.performance_analysis, name="performance"),
    path("payments/", views.payment_analytics, name="payments"),
    # Recipe costing analysis
    path("recipe-costing/", views.recipe_costing_analysis, name="recipe_costing"),
    path("ingredient-trends/", views.ingredient_cost_trends, name="ingredient_trends"),
    path("cost-efficiency/", views.cost_efficiency_analysis, name="cost_efficiency"),
    # Will add more later (COGS, Menu Engineering, etc.)
]

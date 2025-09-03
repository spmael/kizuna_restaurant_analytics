from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    # Main unified dashboard with SSR optimizations
    path("", views.AnalyticsDashboardView.as_view(), name="dashboard"),
    # API endpoints for performance monitoring
    path(
        "api/performance/",
        views.performance_monitor_api,
        name="performance_monitor_api",
    ),
    # Will add more later (COGS, Menu Engineering, etc.)
]

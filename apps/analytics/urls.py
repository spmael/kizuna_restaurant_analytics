from django.http import HttpResponse
from django.urls import path


def temporary_analytics_cogs_view(request):
    """Temporary analytics cogs view for testing."""
    return HttpResponse("Analytics functionality coming soon!")


app_name = "analytics"

urlpatterns = [
    path("cogs/", temporary_analytics_cogs_view, name="cogs"),
    # TODO: Add more analytics URLs
]

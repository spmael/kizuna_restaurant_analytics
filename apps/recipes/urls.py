from django.http import HttpResponse
from django.urls import path


def temporary_recipes_list_view(request):
    """Temporary recipes list view for testing."""
    return HttpResponse("Recipes functionality coming soon!")


app_name = "recipes"

urlpatterns = [
    path("list/", temporary_recipes_list_view, name="list"),
    # TODO: Add more recipes URLs
]

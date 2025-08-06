from django.http import HttpResponse
from django.urls import path


def temporary_upload_view(request):
    """Temporary upload view for testing."""
    return HttpResponse("Upload functionality coming soon!")


app_name = "data_management"

urlpatterns = [
    path("upload/", temporary_upload_view, name="upload"),
    # TODO: Add more data management URLs
]

from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
]
from django.urls import path

from . import views

app_name = "data_management"

urlpatterns = [
    path("", views.DataUploadView.as_view(), name="upload"),
    path("list/", views.DataUploadListView.as_view(), name="upload_list"),
    path(
        "detail/<uuid:pk>/", views.DataUploadDetailView.as_view(), name="upload_detail"
    ),
    path("progress/<uuid:upload_id>/", views.upload_progress, name="upload_progress"),
    path("dashboard/", views.dashboard_stats, name="dashboard"),
    path("quality/", views.data_quality_report, name="quality_report"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
]

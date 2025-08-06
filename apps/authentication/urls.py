from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "authentication"

urlpatterns = [
    # Authentication URLs
    path("register/", views.UserRegistrationView.as_view(), name="register"),
    path("login/", views.user_login_view, name="login"),
    path("logout/", views.user_logout_view, name="logout"),
    # Password Reset URLs
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="authentication/password_reset.html",
            email_template_name="authentication/password_reset_email.html",
            success_url='/auth/password-reset/done/',
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="authentication/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="authentication/password_reset_confirm.html",
            success_url='/auth/password-reset-complete/',
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset-complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="authentication/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    
    # Profile URLs
    path("profile/", views.UserProfileView.as_view(), name="profile"),

    # HTMX endpoints
    path("check-email/", views.check_email_availability, name="check_email"),
]

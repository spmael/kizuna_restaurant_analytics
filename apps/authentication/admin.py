from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for User model."""

    list_display = [
        "email",
        "username",
        "first_name",
        "last_name",
        "role",
        "restaurant_name",
        "is_active",
        "date_joined",
    ]
    list_filter = ["role", "is_active", "is_email_verified", "date_joined"]
    search_fields = ("email", "first_name", "last_name", "username", "restaurant_name")
    ordering = ("date_joined",)

    fieldsets = BaseUserAdmin.fieldsets + (
        (_("Restaurant info"), {"fields": ("role", "restaurant_name", "phone")}),
        (_("Verification"), {"fields": ("is_email_verified", "last_login_ip")}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (_("Restaurant info"), {"fields": ("role", "restaurant_name", "phone")}),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for UserProfile model."""

    list_display = ["user", "timezone", "language", "receive_notifications"]
    list_filter = ["timezone", "language", "receive_notifications"]
    search_fields = ["user__email", "user__username"]

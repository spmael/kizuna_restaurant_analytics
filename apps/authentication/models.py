from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Custom user model for the authentication app."""

    ROLE_CHOICES = [
        ("admin", _("Administrator")),
        ("manager", _("Restaurant Manager")),
        ("analyst", _("Analytics Specialist")),
        ("viewer", _("Viewer")),
    ]

    email = models.EmailField(_("Email address"), unique=True)
    first_name = models.CharField(_("First name"), max_length=150, blank=True)
    last_name = models.CharField(_("Last name"), max_length=150, blank=True)
    role = models.CharField(
        _("Role"),
        max_length=20,
        choices=ROLE_CHOICES,
        default="viewer",
    )
    phone = models.CharField(_("Phone number"), max_length=20, blank=True)
    restaurant_name = models.CharField(
        _("Restaurant name"), max_length=100, blank=True, null=True
    )
    is_email_verified = models.BooleanField(_("Email verified"), default=False)
    last_login_ip = models.GenericIPAddressField(
        _("Last login IP"), blank=True, null=True
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        db_table = "auth_user"

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    def get_full_name(self):
        """Return the full name of the user."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.username

    def get_short_name(self):
        """Return the short name of the user."""
        return self.first_name or self.username


class UserProfile(models.Model):
    """Extended user profile model for additional user information."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    bio = models.TextField(_("Bio"), blank=True)
    avatar = models.ImageField(_("Avatar"), upload_to="avatars/", blank=True, null=True)
    timezone = models.CharField(_("Timezone"), max_length=100, default="Africa/Douala")
    language = models.CharField(_("Language"), max_length=10, default="fr")
    receive_notifications = models.BooleanField(
        _("Receive notifications"), default=True
    )

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")
        db_table = "auth_user_profile"

    def __str__(self):
        return f"{self.user.get_full_name()} Profile"

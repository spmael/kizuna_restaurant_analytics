from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AuthenticationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.authentication"
    verbose_name = _("Authentication")

    def ready(self):
        # import signal handlers
        try:
            import apps.authentication.signals
        except ImportError:
            pass

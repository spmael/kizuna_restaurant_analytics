import os

from config.settings.base import *  # noqa

# Set default environment variables for development
os.environ.setdefault(
    "SECRET_KEY", "django-insecure-development-key-change-in-production"
)
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Debug toolbar settings
INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware"
] + MIDDLEWARE  # noqa: F405

# Debug toolbar configuration
INTERNAL_IPS = [
    "127.0.0.1",
    "localhost",
]

# Allow all hosts in development
ALLOWED_HOSTS = ["*"]

# Database configuration - Override with SQLite for development
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

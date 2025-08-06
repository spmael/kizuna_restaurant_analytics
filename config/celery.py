import os

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("kizuna_restaurant_analytics")

# configur celery using the django settings module.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover celery tasks in all installed apps.
app.autodiscover_tasks()


@app.task
def debug_task(self):
    print(f"Request: {self.request!r}")

"""
Pytest configuration for Django tests
"""

import os
import sys

import django
from django.conf import settings

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.testing")

# Configure Django
django.setup()


# Ensure Django is configured before any tests run
def pytest_configure():
    """Configure Django for testing"""
    if not settings.configured:
        django.setup()

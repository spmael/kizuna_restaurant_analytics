# 🚀 Phase 1: Core Infrastructure Setup Guide
## Kizuna Restaurant Analytics Platform

This guide will walk you through setting up the foundational infrastructure for your restaurant analytics platform.

## 📋 Prerequisites

Before we begin, ensure you have:
- Python 3.9+ installed
- Node.js 16+ and npm installed
- PostgreSQL 13+ installed
- Redis installed (for Celery)
- Git installed
- Docker and Docker Compose (optional but recommended)

## Step 1: Project Initialization

### 1.1 Create Project Directory and Virtual Environment

```bash
# Create main project directory
mkdir kizuna_restaurant_analytics
cd kizuna_restaurant_analytics

# Create and activate virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 1.2 Initialize Git Repository

```bash
git init
touch .gitignore README.md
```

### 1.3 Create .gitignore File

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Django
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal
media/
staticfiles/

# Environment variables
.env
.env.local
.env.production

# Virtual environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Node.js (for frontend)
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Build outputs
build/
dist/

# Logs
logs/
*.log

# Data files (keep structure but not actual data)
data/raw/*
data/processed/*
data/analysis_output/*
data/models/*
!data/raw/.gitkeep
!data/processed/.gitkeep
!data/analysis_output/.gitkeep
!data/models/.gitkeep

# Uploaded files
media/uploads/*
media/exports/*
!media/uploads/.gitkeep
!media/exports/.gitkeep
```

## Step 2: Django Project Setup

### 2.1 Install Core Dependencies

Create `requirements.txt`:

```txt
# Django Core
Django==4.2.7
djangorestframework==3.14.0
django-cors-headers==4.3.1
django-environ==0.11.2
django-extensions==3.2.3

# Database
psycopg2-binary==2.9.9
django-timescaledb==0.2.13

# Authentication
djangorestframework-simplejwt==5.3.0
django-allauth==0.57.0

# Background Tasks
celery==5.3.4
redis==5.0.1
django-celery-beat==2.5.0
django-celery-results==2.5.1

# Data Processing
pandas==2.1.3
numpy==1.25.2
openpyxl==3.1.2
xlrd==2.0.1

# Development
django-debug-toolbar==4.2.0
pytest-django==4.6.0
black==23.11.0
flake8==6.1.0

# Production
gunicorn==21.2.0
whitenoise==6.6.0
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 2.2 Create Django Project Structure

```bash
# Create the main Django project
django-admin startproject config .

# Create apps directory
mkdir apps
touch apps/__init__.py

# Create individual Django apps
cd apps
django-admin startapp core
django-admin startapp authentication
django-admin startapp data_management
django-admin startapp restaurant_data
django-admin startapp recipes
django-admin startapp analytics
django-admin startapp reports
django-admin startapp api
cd ..
```

### 2.3 Create Additional Directory Structure

```bash
# Create data engineering directory
mkdir -p data_engineering/{extractors,transformers,loaders,pipelines,quality,orchestration,config}
touch data_engineering/__init__.py
touch data_engineering/extractors/__init__.py
touch data_engineering/transformers/__init__.py
touch data_engineering/loaders/__init__.py
touch data_engineering/pipelines/__init__.py
touch data_engineering/quality/__init__.py
touch data_engineering/orchestration/__init__.py
touch data_engineering/config/__init__.py

# Create data science directory
mkdir -p data_science/{models,analyzers,feature_engineering,experiments,utils,deployment}
touch data_science/__init__.py
touch data_science/models/__init__.py
touch data_science/analyzers/__init__.py
touch data_science/feature_engineering/__init__.py
touch data_science/experiments/__init__.py
touch data_science/utils/__init__.py
touch data_science/deployment/__init__.py

# Create data directories
mkdir -p data/{raw,processed,analysis_output,models,sample}
touch data/raw/.gitkeep
touch data/processed/.gitkeep
touch data/analysis_output/.gitkeep
touch data/models/.gitkeep

# Create other directories
mkdir -p tests/{unit,integration,e2e,fixtures}
mkdir -p scripts
mkdir -p docs
mkdir -p deployment
mkdir -p logs
mkdir -p media/{uploads,exports}
mkdir -p static

# Add __init__.py files
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
touch tests/e2e/__init__.py
touch scripts/__init__.py
```

## Step 3: Django Configuration

### 3.1 Environment Configuration

Create `.env.example`:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
DJANGO_SETTINGS_MODULE=config.settings.development

# Database
DB_NAME=kizuna_analytics
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# File Storage
MEDIA_ROOT=/path/to/media
STATIC_ROOT=/path/to/static

# Email (for production)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

Copy to `.env`:

```bash
cp .env.example .env
```

### 3.2 Settings Configuration

Create `config/settings/` directory and files:

```bash
mkdir config/settings
touch config/settings/__init__.py
```

**config/settings/base.py:**

```python
import os
from pathlib import Path
import environ
from celery.schedules import crontab

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Environment variables
env = environ.Env(
    DEBUG=(bool, False)
)

# Read .env file
environ.Env.read_env(BASE_DIR / '.env')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = []

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_celery_beat',
    'django_celery_results',
    'django_extensions',
]

LOCAL_APPS = [
    'apps.core',
    'apps.authentication',
    'apps.data_management',
    'apps.restaurant_data',
    'apps.recipes',
    'apps.analytics',
    'apps.reports',
    'apps.api',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.middleware.RequestLoggingMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
        'OPTIONS': {
            'options': '-c default_transaction_isolation=serializable'
        },
        'TEST': {
            'NAME': 'test_' + env('DB_NAME'),
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'fr'  # French is primary language in Cameroon
TIME_ZONE = 'Africa/Douala'  # Cameroon timezone (UTC+1)
USE_I18N = True
USE_L10N = True  # Enable localized formatting
USE_TZ = True

# Additional language support
LANGUAGES = [
    ('fr', 'Français'),
    ('en', 'English'),  # English is also official in Cameroon
]

# Locale paths for translations
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Number and currency formatting for Cameroon
USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = ' '  # French convention uses space
DECIMAL_SEPARATOR = ','   # French convention uses comma

# Currency settings (CFA Franc)
CURRENCY = 'XAF'
CURRENCY_SYMBOL = 'FCFA'

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'authentication.User'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'apps.api.pagination.CustomPageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

# JWT Settings
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=60),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# Celery Configuration
CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    'weekly-data-update': {
        'task': 'apps.core.tasks.weekly_data_update',
        'schedule': crontab(hour=2, minute=0, day_of_week=1),  # Monday 2 AM
    },
    'monthly-analytics-refresh': {
        'task': 'apps.analytics.tasks.monthly_analytics_refresh',
        'schedule': crontab(hour=3, minute=0, day=1),  # 1st of month 3 AM
    },
    'daily-data-quality-check': {
        'task': 'data_engineering.quality.tasks.daily_quality_check',
        'schedule': crontab(hour=1, minute=0),  # Daily 1 AM
    },
}

# CORS Settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React dev server
    "http://127.0.0.1:3000",
]

CORS_ALLOW_CREDENTIALS = True

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB

# Data Processing Configuration
DATA_PROCESSING = {
    'BATCH_SIZE': 1000,
    'MAX_WORKERS': 4,
    'TIMEOUT_SECONDS': 3600,
    'RETRY_COUNT': 3,
    'QUALITY_THRESHOLD': 0.95,
}

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

**config/settings/development.py:**

```python
from .base import *

# Debug toolbar
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE

# Debug toolbar configuration
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

# Allow all hosts for development
ALLOWED_HOSTS = ['*']

# Database for development (can use SQLite for quick setup)
# Uncomment if you want to use SQLite for initial development
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

**config/settings/production.py:**

```python
from .base import *

# Security settings
DEBUG = False
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 31536000
SECURE_REDIRECT_EXEMPT = []
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'

# Static files for production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

**config/settings/testing.py:**

```python
from .base import *

# Test database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Faster password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable logging during tests
LOGGING_CONFIG = None
```

### 3.3 Update Django Settings Import

Edit `config/settings/__init__.py`:

```python
import os

# Default to development settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
```

### 3.4 Configure URLs

**config/urls.py:**

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({"status": "ok", "message": "Kizuna Analytics API is running"})

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Health check
    path('health/', health_check, name='health_check'),
    
    # API
    path('api/', include('apps.api.urls')),
    
    # App URLs
    path('auth/', include('apps.authentication.urls')),
    path('data/', include('apps.data_management.urls')),
    path('recipes/', include('apps.recipes.urls')),
    path('analytics/', include('apps.analytics.urls')),
    path('reports/', include('apps.reports.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns

# Custom error handlers
handler404 = 'apps.core.views.custom_404'
handler500 = 'apps.core.views.custom_500'
```

### 3.5 Configure Celery

**config/celery.py:**

```python
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('kizuna_analytics')

# Configure Celery using settings from Django settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
```

**config/__init__.py:**

```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

## Step 4: Database Setup

### 4.1 Create PostgreSQL Database

```bash
# Connect to PostgreSQL (adjust for your setup)
psql -U postgres

# Create database and user
CREATE DATABASE kizuna_analytics;
CREATE USER kizuna_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE kizuna_analytics TO kizuna_user;

# Exit psql
\q
```

### 4.2 Update .env File

```env
DB_NAME=kizuna_analytics
DB_USER=kizuna_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

## Step 5: Initial App Configuration

Now let's configure each app. I'll show you the next steps in the following response to keep this manageable.

## Next Steps

1. ✅ Project structure created
2. ✅ Django configuration complete
3. ✅ Database setup ready
4. 🔄 **Next**: Configure individual apps (core, authentication, etc.)
5. ⏳ Create models and migrations
6. ⏳ Set up API structure
7. ⏳ Docker configuration

**Ready for the next part?** Let me know when you've completed these steps and I'll guide you through configuring the individual Django apps!
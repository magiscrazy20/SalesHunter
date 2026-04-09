import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-change-me-in-production'
)

DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1')

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django_celery_beat',
    'leads',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'wholesalehunter.urls'

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
                'leads.context_processors.recent_sessions',
            ],
        },
    },
]

WSGI_APPLICATION = 'wholesalehunter.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('DB_NAME', BASE_DIR / 'db.sqlite3'),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', ''),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()
]

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', 'True').lower() in ('true', '1')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Celery
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Lead Master API keys
APOLLO_API_KEY = os.environ.get('APOLLO_API_KEY', '')
NVIDIA_API_KEY = os.environ.get('NVIDIA_API_KEY', '')
APIFY_GOOGLE_MAP_API_KEY = os.environ.get('APIFY_GOOGLE_MAP_API_KEY', '')
APIFY_LINKEDIN_API_KEY = os.environ.get('APIFY_LINKEDIN_API_KEY', '')
NVIDIA_MODELS = [
    'meta/llama-3.1-8b-instruct',
    'google/gemma-2-9b-it',
    'meta/llama-3.3-70b-instruct',
]

# Public site URL used for tracking pixels in emails
SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000')

# SalesHunter config
SALESHUNTER = {
    'DAILY_SCRAPE_TARGET': 1000,
    'DAILY_EMAIL_TARGET': 1000,
    'DAILY_FORM_TARGET': 1000,
    'MIN_LEAD_SCORE': 40,
    'FOLLOW_UP_DAYS': [1, 3, 7, 14],
    'SENDING_DOMAINS_COUNT': 15,
    'EMAILS_PER_DOMAIN': 65,
    'MONTHLY_CHURN_RATE': 0.05,
    # Auto-exclusion thresholds
    'COUNTRY_PAUSE_THRESHOLD': 200,  # leads with 0 closes
    'LEAD_TYPE_DEPRIORITIZE_RATE': 0.005,  # <0.5% close rate after 500+
    'SOURCE_REDUCE_RATE': 0.01,  # <1% reply rate after 1000+
    'EMAIL_OPEN_RATE_MIN': 0.10,  # rotate domain below 10%
    # API keys (set via environment)
    'APOLLO_API_KEY': os.environ.get('APOLLO_API_KEY', ''),
    'INSTANTLY_API_KEY': os.environ.get('INSTANTLY_API_KEY', ''),
    'CLAUDE_API_KEY': os.environ.get('CLAUDE_API_KEY', ''),
    'HUBSPOT_API_KEY': os.environ.get('HUBSPOT_API_KEY', ''),
    # Rozper defaults
    'COMPANY_NAME': 'Rozper',
    'CONTACT_NAME': 'Sajid Kapadia',
    'CONTACT_EMAIL': os.environ.get('ROZPER_EMAIL', 'sajid@rozper.com'),
}


"""
Django settings for core project.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/
"""
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Security settings
SECRET_KEY = os.environ.get('SECRET_KEY')
#SECRET_KEY = "GOKUL-9353617108"

# Debug mode - Set to False for production, True for development
DEBUG = False

ALLOWED_HOSTS = ['.onrender.com']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
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
    'django.middleware.gzip.GZipMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'CONN_MAX_AGE': 600,  # Connection pooling - reuse connections for 10 minutes
        'OPTIONS': {
            'timeout': 20,  # Increase timeout to prevent database locks
        }
    }
}

# Enable persistent connections
CONN_MAX_AGE = 600


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Caching configuration - Use locmem for in-process caching
# Note: Using session caching only, not page-level middleware caching
# This allows API endpoints and dynamic pages to always serve fresh data
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 600,  # Cache timeout 10 minutes
        'OPTIONS': {
            'MAX_ENTRIES': 5000,
        }
    }
}

# Session cache to speed up session access
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Session configuration for performance
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False  # Always False for local development
SESSION_SAVE_EVERY_REQUEST = False  # Don't save session on every request

# HTTP caching headers for browser caching
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_SECURITY_POLICY = {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'"],
        'style-src': ["'self'", "'unsafe-inline'", 'fonts.googleapis.com'],
        'font-src': ["'self'", 'fonts.gstatic.com'],
        'connect-src': ["'self'"],
        'img-src': ["'self'", 'data:'],
    }
else:
    # Development: disable all security headers
    SECURE_BROWSER_XSS_FILTER = False

# Optimize static files
WHITENOISE_AUTOREFRESH = False  # Turn off auto-refresh in production
WHITENOISE_USE_FINDERS = True  # Use Django finders

# Database query optimization
DATABASES['default']['ATOMIC_REQUESTS'] = False  # Disable atomic requests for better performance with SQLite

# Logging configuration - ERROR level in production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'ERROR',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console'],
            'level': 'ERROR',
        },
    },
}

# Default primary key field type
# https://docs.djangoproject.com/en/6.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

if not DEBUG:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
    # WhiteNoise compression for static files
    WHITENOISE_COMPRESS_OFFLINE = True
    WHITENOISE_COMPRESS_ONLINE = True

# ============================================
# PRODUCTION DEPLOYMENT SETTINGS
# ============================================

# HTTP/HTTPS settings - DISABLED FOR LOCAL DEVELOPMENT
# Never force SSL in development
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Security headers
X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = True

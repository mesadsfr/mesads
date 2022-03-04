"""
Django settings for mesads project.

Generated by 'django-admin startproject' using Django 3.2.9.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

import os
import socket
from pathlib import Path


def parse_env_bool(key, default):
    """Helper function to parse environment variable."""
    value = os.getenv(key)

    if value is None:
        return default
    elif value.lower() in ('yes', 'true' '1', 't'):
        return True
    elif value.lower() in ('no', 'false' '0', 'f', ''):
        return False

    raise ValueError(f'Unknown boolean environment variable {value}')


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = parse_env_bool('DEBUG', True)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/


if DEBUG:
    SECRET_KEY = os.getenv(
        'SECRET_KEY',
        'django-insecure-#tx=c!1uiqr9*e^cz%u2_!7$rl$c4$sg!=m!n$5llbhnxebj@$'
    )
else:
    # SECRET_KEY is mandatory when DEBUG is False
    SECRET_KEY = os.environ['SECRET_KEY']


ALLOWED_HOSTS = [
    part for part in os.getenv('ALLOWED_HOSTS', '').split(';')
    if part
]

# Application definition

INSTALLED_APPS = [
    # According to django-autocomplete-light documentation, DAL moduels must be
    # installed before django.contrib.admin.
    # See: https://django-autocomplete-light.readthedocs.io/en/master/install.html
    'dal',
    'dal_select2',
    'dal_queryset_sequence',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'debug_toolbar',
    'django_registration',

    'mesads.app',
    'mesads.users',
    'mesads.fradm',
]

AUTH_USER_MODEL = 'users.User'

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mesads.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'mesads/templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'mesads.app.context_processors.mesads_settings'
            ],
        },
    },
]

WSGI_APPLICATION = 'mesads.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'mesads'),
        'HOST': os.getenv('DB_HOST', 'db'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'mesads'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'fr-FR'

TIME_ZONE = 'Europe/Paris'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/auth/login/'

# Static configuration
STATIC_ROOT = BASE_DIR / 'static'

STATICFILES_DIRS = [
    ('', BASE_DIR / 'mesads/static'),
    ('@gouvfr', BASE_DIR / 'node_modules/@gouvfr/dsfr/dist/'),
]

MEDIA_ROOT = BASE_DIR / 'uploads'
MEDIA_URL = '/uploads/'

# Redirect to / after login/logout
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Setup INTERNAL_IPS for django-debug-toolbar.
if DEBUG:
    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[:-1] + '1' for ip in ips] + ['127.0.0.1', '10.0.2.2']

# Upload files to S3: https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

MESADS_CONTACT_EMAIL = 'equipe@mesads.fr'


EMAIL_HOST = os.getenv('EMAIL_HOST', 'maildev')
EMAIL_PORT = os.getenv('EMAIL_PORT', 25)
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = parse_env_bool('EMAIL_USE_TLS', False)

# Add configuration below to log SQL queries to console
# LOGGING = {
#     'version': 1,
#     'filters': {
#         'require_debug_true': {
#             '()': 'django.utils.log.RequireDebugTrue',
#         }
#     },
#     'handlers': {
#         'console': {
#             'level': 'DEBUG',
#             'filters': ['require_debug_true'],
#             'class': 'logging.StreamHandler',
#         }
#     },
#     'loggers': {
#         'django.db.backends': {
#             'level': 'DEBUG',
#             'handlers': ['console'],
#         }
#     }
# }

# django-registration: maximum number of days to activate the account
ACCOUNT_ACTIVATION_DAYS = 14

# By default an exception is raised if you try to add an administrator from the
# admin page at
# http://localhost:9400/admin/app/adsmanageradministrator/<id>/change/ because
# too many form values are provided.
# We set a large value to avoid the issue.
DATA_UPLOAD_MAX_NUMBER_FIELDS = 2 ** 16

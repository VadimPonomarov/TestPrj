"""Django settings entry point for TestPrj using modular extra_config package."""

import os
from typing import List

from . import extra_config as _extra_config  # noqa: F401
from .extra_config import BASE_DIR, ROOT_DIR  # noqa: F401
from .extra_config import *  # noqa: F401,F403


def _parse_hosts(raw: str) -> List[str]:
    return [host for host in (value.strip() for value in raw.replace(",", " ").split()) if host]


SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-placeholder")
DEBUG = os.getenv("DJANGO_DEBUG", os.getenv("DEBUG", "0")).lower() in {"1", "true", "yes", "on"}
ALLOWED_HOSTS = _parse_hosts(os.getenv("DJANGO_ALLOWED_HOSTS", "")) or ["localhost", "127.0.0.1"]


# Application definition

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    #
    "parser_app",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": os.getenv("SQL_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.getenv("SQL_DATABASE", "mydb"),
        "USER": os.getenv("SQL_USER", "myuser"),
        "PASSWORD": os.getenv("SQL_PASSWORD", "mypassword"),
        "HOST": os.getenv("SQL_HOST", "127.0.0.1"),
        "PORT": os.getenv("SQL_PORT", "5432"),
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "static/"

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Temp directory for temporary files
TEMP_DIR = os.path.join(BASE_DIR, 'temp')

# Create directories if they don't exist
os.makedirs(MEDIA_ROOT, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
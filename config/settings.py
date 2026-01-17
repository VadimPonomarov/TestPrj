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

INSTALLED_APPS = _extra_config.INSTALLED_APPS

MIDDLEWARE = _extra_config.MIDDLEWARE

ROOT_URLCONF = _extra_config.ROOT_URLCONF

TEMPLATES = _extra_config.TEMPLATES

WSGI_APPLICATION = _extra_config.WSGI_APPLICATION


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = _extra_config.DATABASES


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = _extra_config.AUTH_PASSWORD_VALIDATORS


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = _extra_config.LANGUAGE_CODE

TIME_ZONE = _extra_config.TIME_ZONE

USE_I18N = _extra_config.USE_I18N

USE_TZ = _extra_config.USE_TZ


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = _extra_config.STATIC_URL

STATIC_ROOT = _extra_config.STATIC_ROOT

MEDIA_URL = _extra_config.MEDIA_URL
MEDIA_ROOT = _extra_config.MEDIA_ROOT

# Temp directory for temporary files
TEMP_DIR = _extra_config.TEMP_DIR

# Create directories if they don't exist
os.makedirs(_extra_config.STATIC_ROOT, exist_ok=True)
os.makedirs(_extra_config.MEDIA_ROOT, exist_ok=True)
os.makedirs(_extra_config.TEMP_DIR, exist_ok=True)
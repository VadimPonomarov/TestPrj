"""Modularized Django settings for TestPrj."""

from .environment import BASE_DIR, ROOT_DIR  # noqa: F401
from .apps_config import (  # noqa: F401
    INSTALLED_APPS,
    MIDDLEWARE,
    ROOT_URLCONF,
    TEMPLATES,
    WSGI_APPLICATION,
)
from .database_config import DATABASES  # noqa: F401
from .auth_config import AUTH_PASSWORD_VALIDATORS  # noqa: F401
from .internationalization_config import LANGUAGE_CODE, TIME_ZONE, USE_I18N, USE_TZ  # noqa: F401
from .static_config import STATIC_URL, STATIC_ROOT, MEDIA_URL, MEDIA_ROOT, TEMP_DIR  # noqa: F401
from .rest_framework_config import REST_FRAMEWORK  # noqa: F401
from .swagger_config import SWAGGER_SETTINGS, SWAGGER_USE_SESSION_AUTH  # noqa: F401
from .cors_config import (  # noqa: F401
    CORS_ALLOWED_ORIGINS,
    CORS_ALLOW_CREDENTIALS,
    CORS_ALLOW_HEADERS,
    CSRF_TRUSTED_ORIGINS,
)

__all__ = [
    "BASE_DIR",
    "ROOT_DIR",
    "INSTALLED_APPS",
    "MIDDLEWARE",
    "ROOT_URLCONF",
    "TEMPLATES",
    "WSGI_APPLICATION",
    "DATABASES",
    "AUTH_PASSWORD_VALIDATORS",
    "LANGUAGE_CODE",
    "TIME_ZONE",
    "USE_I18N",
    "USE_TZ",
    "STATIC_URL",
    "STATIC_ROOT",
    "MEDIA_URL",
    "MEDIA_ROOT",
    "TEMP_DIR",
    "REST_FRAMEWORK",
    "SWAGGER_SETTINGS",
    "SWAGGER_USE_SESSION_AUTH",
    "CORS_ALLOWED_ORIGINS",
    "CORS_ALLOW_CREDENTIALS",
    "CORS_ALLOW_HEADERS",
    "CSRF_TRUSTED_ORIGINS",
]

"""Database configuration for TestPrj."""

import os

DATABASES = {
    "default": {
        "ENGINE": os.getenv("SQL_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.getenv("SQL_DATABASE", "mydb"),
        "USER": os.getenv("SQL_USER", "myuser"),
        "PASSWORD": os.getenv("SQL_PASSWORD", "mypassword"),
        "HOST": os.getenv("SQL_HOST", "127.0.0.1"),
        "PORT": os.getenv("SQL_PORT", "5432"),
        "OPTIONS": {
            "options": os.getenv("SQL_OPTIONS", "-c client_encoding=UTF8"),
        },
    }
}

__all__ = ["DATABASES"]

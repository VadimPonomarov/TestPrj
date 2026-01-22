"""Database configuration for TestPrj."""

import os

from typing import Any, Dict

engine = os.getenv("SQL_ENGINE", "django.db.backends.postgresql")

default_db: Dict[str, Any] = {
    "ENGINE": engine,
    "NAME": os.getenv("SQL_DATABASE", "mydb"),
    "USER": os.getenv("SQL_USER", "myuser"),
    "PASSWORD": os.getenv("SQL_PASSWORD", "mypassword"),
    "HOST": os.getenv("SQL_HOST", "127.0.0.1"),
    "PORT": os.getenv("SQL_PORT", "5432"),
}

if "postgres" in engine:
    default_db["OPTIONS"] = {
        "options": os.getenv("SQL_OPTIONS", "-c client_encoding=UTF8"),
    }

DATABASES = {"default": default_db}

__all__ = ["DATABASES"]

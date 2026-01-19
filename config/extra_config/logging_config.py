"""Logging configuration for TestPrj."""

import os
from pathlib import Path

from .environment import BASE_DIR


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


LOG_ENABLED = _env_bool("LOG_ENABLED", True)

if not LOG_ENABLED:
    LOGGING_CONFIG = None
    LOGGING = {}
else:
    LOGGING_CONFIG = "logging.config.dictConfig"

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    DJANGO_LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", LOG_LEVEL).upper()
    SQL_LOG_LEVEL = os.getenv("SQL_LOG_LEVEL", "WARNING").upper()

    LOG_CONSOLE_ENABLED = _env_bool("LOG_CONSOLE_ENABLED", True)
    LOG_FILE_ENABLED = _env_bool("LOG_FILE_ENABLED", False)

    LOG_DIR = Path(os.getenv("LOG_DIR", str(Path(BASE_DIR) / "logs")))
    LOG_FILE_NAME = os.getenv("LOG_FILE_NAME", "app.log")
    LOG_FILE_PATH = Path(os.getenv("LOG_FILE_PATH", str(LOG_DIR / LOG_FILE_NAME)))

    LOG_MAX_BYTES = _env_int("LOG_MAX_BYTES", 10 * 1024 * 1024)
    LOG_BACKUP_COUNT = _env_int("LOG_BACKUP_COUNT", 5)

    if LOG_FILE_ENABLED:
        LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    formatters = {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        }
    }

    handlers = {}
    root_handlers = []

    if LOG_CONSOLE_ENABLED:
        handlers["console"] = {
            "class": "logging.StreamHandler",
            "level": LOG_LEVEL,
            "formatter": "standard",
        }
        root_handlers.append("console")

    if LOG_FILE_ENABLED:
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": LOG_LEVEL,
            "formatter": "standard",
            "filename": str(LOG_FILE_PATH),
            "maxBytes": LOG_MAX_BYTES,
            "backupCount": LOG_BACKUP_COUNT,
            "encoding": "utf-8",
        }
        root_handlers.append("file")

    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "root": {
            "level": LOG_LEVEL,
            "handlers": root_handlers,
        },
        "loggers": {
            "django": {
                "level": DJANGO_LOG_LEVEL,
                "propagate": True,
            },
            "django.db.backends": {
                "level": SQL_LOG_LEVEL,
                "propagate": True,
            },
            "parser_app": {
                "level": LOG_LEVEL,
                "propagate": True,
            },
            "core": {
                "level": LOG_LEVEL,
                "propagate": True,
            },
        },
    }


__all__ = ["LOGGING", "LOGGING_CONFIG", "LOG_ENABLED"]

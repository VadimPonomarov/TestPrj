"""CORS/CSRF configuration shared across environments."""

import os

from corsheaders.defaults import default_headers


def _parse_space_separated(raw: str) -> list[str]:
    return [
        value
        for value in (part.strip() for part in raw.replace(",", " ").split())
        if value
    ]


DEFAULT_ORIGINS = [
    "http://localhost",
    "http://localhost:80",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "http://0.0.0.0:8000",
    "http://web:8000",
    "http://nginx",
]


_env_origins = _parse_space_separated(os.getenv("CORS_ALLOWED_ORIGINS", ""))
CORS_ALLOWED_ORIGINS = _env_origins or DEFAULT_ORIGINS
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = list(default_headers) + ["x-requested-with"]


_env_csrf = _parse_space_separated(os.getenv("CSRF_TRUSTED_ORIGINS", ""))
CSRF_TRUSTED_ORIGINS = _env_csrf or [
    origin.rstrip("/") for origin in CORS_ALLOWED_ORIGINS if origin.startswith("http")
]


__all__ = [
    "CORS_ALLOWED_ORIGINS",
    "CORS_ALLOW_CREDENTIALS",
    "CORS_ALLOW_HEADERS",
    "CSRF_TRUSTED_ORIGINS",
]

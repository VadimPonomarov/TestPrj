"""Static and media files configuration for TestPrj."""

import os

from .environment import BASE_DIR

STATIC_URL = "static/"

STATIC_ROOT = os.path.join(BASE_DIR, "static")

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

TEMP_DIR = os.path.join(BASE_DIR, "temp")

os.makedirs(STATIC_ROOT, exist_ok=True)
os.makedirs(MEDIA_ROOT, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

__all__ = [
    "STATIC_URL",
    "STATIC_ROOT",
    "MEDIA_URL",
    "MEDIA_ROOT",
    "TEMP_DIR",
]

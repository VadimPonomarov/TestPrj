"""Utility to initialise Django context for Scrapy components."""

import os
import sys
from pathlib import Path

import django
from django.apps import apps


def setup_django(default_settings: str = "config.settings") -> None:
    """Configure Django so Scrapy can reuse project models/serializers."""

    project_root = Path(__file__).resolve().parents[2]
    project_path = str(project_root)
    if project_path not in sys.path:
        sys.path.append(project_path)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", default_settings)
    os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

    if not apps.ready:
        django.setup()

"""Utility to initialize Django environment for standalone scripts."""

from pathlib import Path
import os
import sys
import django


def setup_django() -> None:
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

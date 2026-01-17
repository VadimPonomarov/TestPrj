"""Environment configuration for TestPrj."""

import os
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BASE_DIR

ENV_FILES: Iterable[Path] = (
    ROOT_DIR / ".env",
)

for env_file in ENV_FILES:
    if env_file.exists():
        load_dotenv(env_file, override=True)

__all__ = ["BASE_DIR", "ROOT_DIR"]

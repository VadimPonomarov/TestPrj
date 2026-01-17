"""Environment configuration for TestPrj."""

import os
from pathlib import Path
from typing import Iterable, Tuple

from dotenv import load_dotenv

if os.name == "nt":
    os.environ.setdefault("PGCLIENTENCODING", "WIN1251")
else:
    os.environ.setdefault("PGCLIENTENCODING", "UTF8")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BASE_DIR

ENV_FILES: Iterable[Tuple[Path, bool]] = (
    (ROOT_DIR / ".env", False),
    (ROOT_DIR / ".env.local", True),
)

def _should_load(env_file: Path) -> bool:
    if env_file.name == ".env.local" and os.getenv("IS_DOCKER"):
        return False
    return env_file.exists()


for env_file, override in ENV_FILES:
    if _should_load(env_file):
        load_dotenv(env_file, override=override)

__all__ = ["BASE_DIR", "ROOT_DIR"]

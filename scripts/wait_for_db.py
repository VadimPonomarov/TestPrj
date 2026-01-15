import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.load_django import setup_django


MAX_ATTEMPTS_ENV = "DB_WAIT_MAX_ATTEMPTS"
SLEEP_SECONDS_ENV = "DB_WAIT_SLEEP_SECONDS"
DEFAULT_ATTEMPTS = 30
DEFAULT_SLEEP_SECONDS = 1.0


def wait_for_db() -> None:
    setup_django()

    from django.db import connections
    from django.db.utils import OperationalError

    max_attempts = int(os.environ.get(MAX_ATTEMPTS_ENV, DEFAULT_ATTEMPTS))
    sleep_seconds = float(os.environ.get(SLEEP_SECONDS_ENV, DEFAULT_SLEEP_SECONDS))

    attempt = 0
    while True:
        attempt += 1
        try:
            connections["default"].cursor()
        except OperationalError:
            if attempt >= max_attempts:
                raise SystemExit(
                    "Database unavailable after waiting for readiness"
                )
            time.sleep(sleep_seconds)
        else:
            break


if __name__ == "__main__":
    wait_for_db()

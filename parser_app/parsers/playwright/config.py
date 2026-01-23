import os


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if raw == "":
        return default
    try:
        return int(raw)
    except Exception:
        return default


PLAYWRIGHT_NAVIGATION_TIMEOUT_MS = _env_int("PLAYWRIGHT_NAVIGATION_TIMEOUT_MS", 60000)
PLAYWRIGHT_PRELOADER_TIMEOUT_MS = _env_int("PLAYWRIGHT_PRELOADER_TIMEOUT_MS", 20000)

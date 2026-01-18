from __future__ import annotations

import atexit
import threading

from .driver import apply_headers, create_driver


_lock = threading.Lock()
_driver = None


def _is_reuse_enabled() -> bool:
    import os

    return os.getenv("SELENIUM_REUSE_DRIVER", "").strip() in {"1", "true", "True", "yes", "YES"}


def is_reuse_enabled() -> bool:
    return _is_reuse_enabled()


def get_driver():
    """Return a singleton Selenium driver when SELENIUM_REUSE_DRIVER is enabled."""
    global _driver

    if not _is_reuse_enabled():
        raise RuntimeError("Selenium reuse is disabled")

    with _lock:
        if _driver is None:
            _driver = create_driver()
            apply_headers(driver=_driver)
        return _driver


def reset_driver_state(*, driver) -> None:
    try:
        driver.delete_all_cookies()
    except Exception:
        pass


def close_driver() -> None:
    global _driver

    with _lock:
        if _driver is not None:
            try:
                _driver.quit()
            except Exception:
                pass
        _driver = None


atexit.register(close_driver)

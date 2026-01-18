from __future__ import annotations

import atexit
import threading


_lock = threading.Lock()
_playwright = None
_browser = None


def _is_reuse_enabled() -> bool:
    import os

    return os.getenv("PLAYWRIGHT_REUSE_BROWSER", "").strip() in {"1", "true", "True", "yes", "YES"}


def is_reuse_enabled() -> bool:
    return _is_reuse_enabled()


def _start():
    global _playwright, _browser

    if _playwright is not None and _browser is not None:
        return

    from playwright.sync_api import sync_playwright

    _playwright = sync_playwright().start()
    _browser = _playwright.chromium.launch(headless=True)


def get_browser():
    """Return a singleton Playwright browser when PLAYWRIGHT_REUSE_BROWSER is enabled."""
    if not _is_reuse_enabled():
        raise RuntimeError("Playwright reuse is disabled")

    with _lock:
        _start()
        return _browser


def close_browser() -> None:
    global _playwright, _browser

    with _lock:
        if _browser is not None:
            try:
                _browser.close()
            except Exception:
                pass
        _browser = None

        if _playwright is not None:
            try:
                _playwright.stop()
            except Exception:
                pass
        _playwright = None


atexit.register(close_browser)

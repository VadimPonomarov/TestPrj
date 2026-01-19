from __future__ import annotations

import atexit
import asyncio
from concurrent.futures import ThreadPoolExecutor
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

    def _do_start():
        from playwright.sync_api import sync_playwright

        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        return pw, browser

    loop_running = False
    try:
        asyncio.get_running_loop()
        loop_running = True
    except RuntimeError:
        loop_running = False

    if loop_running:
        with ThreadPoolExecutor(max_workers=1) as executor:
            _playwright, _browser = executor.submit(_do_start).result()
    else:
        _playwright, _browser = _do_start()


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

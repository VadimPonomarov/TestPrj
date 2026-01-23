from __future__ import annotations

import atexit
import asyncio
import concurrent.futures
import os
import threading


_lock = threading.Lock()
_playwright = None
_browser = None
_thread: threading.Thread | None = None
_thread_id: int | None = None
_startup_error: BaseException | None = None
_loop: asyncio.AbstractEventLoop | None = None
_startup_event = threading.Event()


def _is_reuse_enabled() -> bool:
    import os

    return os.getenv("PLAYWRIGHT_REUSE_BROWSER", "").strip() in {"1", "true", "True", "yes", "YES"}


def is_reuse_enabled() -> bool:
    return _is_reuse_enabled()


def _thread_main() -> None:
    global _playwright, _browser, _thread_id, _startup_error, _loop

    from playwright.async_api import async_playwright

    pw = None
    browser = None
    loop: asyncio.AbstractEventLoop | None = None
    try:
        _thread_id = threading.get_ident()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _startup():
            nonlocal pw, browser
            pw = await async_playwright().start()

            import os

            proxy_server = os.getenv("PLAYWRIGHT_PROXY_SERVER", "").strip()
            proxy = None
            if proxy_server:
                proxy = {
                    "server": proxy_server,
                    "username": os.getenv("PLAYWRIGHT_PROXY_USERNAME", "").strip() or None,
                    "password": os.getenv("PLAYWRIGHT_PROXY_PASSWORD", "").strip() or None,
                }
                proxy = {k: v for k, v in proxy.items() if v}

            args = [
                "--disable-dev-shm-usage",
                "--blink-settings=imagesEnabled=false",
            ]

            browser = await pw.chromium.launch(
                headless=True,
                args=args,
                proxy=proxy,
            )

        try:
            loop.run_until_complete(_startup())
        except BaseException as exc:
            with _lock:
                _startup_error = exc
            _startup_event.set()
            return

        with _lock:
            _playwright = pw
            _browser = browser
            _loop = loop
            _startup_error = None

        _startup_event.set()
        loop.run_forever()
    finally:
        try:
            if loop is not None and not loop.is_closed():
                async def _shutdown():
                    if browser is not None:
                        try:
                            await browser.close()
                        except Exception:
                            pass
                    if pw is not None:
                        try:
                            await pw.stop()
                        except Exception:
                            pass

                try:
                    loop.run_until_complete(_shutdown())
                except Exception:
                    pass
                try:
                    loop.close()
                except Exception:
                    pass
        finally:
            with _lock:
                _browser = None
                _playwright = None
                _thread_id = None
                _loop = None


def _start():
    global _thread

    with _lock:
        if _thread is not None and _thread.is_alive() and _browser is not None:
            return

        # Reset previous startup error before creating a new thread.
        global _startup_error
        _startup_error = None
        _startup_event.clear()

        _thread = threading.Thread(target=_thread_main, name="playwright-browser-singleton", daemon=True)
        _thread.start()

    # Wait until the browser is available.
    if not _startup_event.wait(timeout=10):
        raise RuntimeError("Playwright singleton browser failed to start")

    with _lock:
        if _startup_error is not None:
            raise RuntimeError("Playwright singleton browser failed to start") from _startup_error
        if _browser is None or _loop is None:
            raise RuntimeError("Playwright singleton browser failed to start")


def run_in_browser_thread(fn):
    """Execute an async callable in the singleton Playwright asyncio loop.

    The provided callable must return an awaitable (coroutine).
    """

    _start()
    with _lock:
        loop = _loop
        browser = _browser
        owner_id = _thread_id

    if loop is None or browser is None:
        raise RuntimeError("Playwright singleton browser is not available")
    if owner_id is not None and threading.get_ident() == owner_id:
        raise RuntimeError("run_in_browser_thread cannot be called from the Playwright owner thread")

    coro = fn(browser)
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    timeout_raw = os.getenv("PLAYWRIGHT_JOB_TIMEOUT_S", "").strip()
    timeout_s: float | None
    if timeout_raw == "":
        timeout_s = 90.0
    else:
        try:
            timeout_s = float(timeout_raw)
        except Exception:
            timeout_s = 90.0

    if timeout_s is not None and timeout_s > 0:
        try:
            return future.result(timeout=timeout_s)
        except concurrent.futures.TimeoutError as exc:
            raise TimeoutError(f"Playwright job timed out after {timeout_s:.0f}s") from exc

    return future.result()


def get_browser():
    """Return the singleton Playwright browser.

    NOTE: The returned browser must only be used from within the Playwright browser
    thread. Prefer `run_in_browser_thread`.
    """

    _start()
    with _lock:
        return _browser


def close_browser() -> None:
    global _thread

    with _lock:
        t = _thread
        _thread = None

    with _lock:
        loop = _loop

    if loop is not None:
        try:
            loop.call_soon_threadsafe(loop.stop)
        except Exception:
            pass

    if t is not None and t.is_alive():
        try:
            t.join(timeout=10)
        except Exception:
            pass


atexit.register(close_browser)

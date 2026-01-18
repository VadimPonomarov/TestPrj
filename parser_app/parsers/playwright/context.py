from __future__ import annotations

import os

from ..config import BROWSER_EXTRA_HEADERS, BROWSER_USER_AGENT


def _block_resources_enabled() -> bool:
    return os.getenv("PLAYWRIGHT_BLOCK_RESOURCES", "").strip() in {
        "1",
        "true",
        "True",
        "yes",
        "YES",
    }


def create_page(*, playwright=None, browser=None):
    if browser is None:
        if playwright is None:
            raise ValueError("Either 'playwright' or 'browser' must be provided")
        browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent=BROWSER_USER_AGENT,
        extra_http_headers=dict(BROWSER_EXTRA_HEADERS),
    )
    page = context.new_page()

    if _block_resources_enabled():
        def _route_handler(route):
            try:
                resource_type = route.request.resource_type
            except Exception:
                resource_type = None

            if resource_type in {"image", "media", "font"}:
                try:
                    route.abort()
                except Exception:
                    route.continue_()
                return

            route.continue_()

        page.route("**/*", _route_handler)
    return browser, context, page

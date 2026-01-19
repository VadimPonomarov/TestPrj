from __future__ import annotations

import os

from ..config import BROWSER_EXTRA_HEADERS, BROWSER_USER_AGENT


def _block_resources_enabled() -> bool:
    raw = os.getenv("PLAYWRIGHT_BLOCK_RESOURCES", "").strip()
    if raw == "":
        return True
    return raw in {"1", "true", "True", "yes", "YES"}


async def create_page(*, browser=None):
    if browser is None:
        raise ValueError("'browser' must be provided")

    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent=BROWSER_USER_AGENT,
        extra_http_headers=dict(BROWSER_EXTRA_HEADERS),
    )
    page = await context.new_page()

    if _block_resources_enabled():
        async def _route_handler(route):
            try:
                resource_type = route.request.resource_type
            except Exception:
                resource_type = None

            if resource_type in {"image", "media", "font"}:
                try:
                    await route.abort()
                except Exception:
                    await route.continue_()
                return

            if resource_type in {"stylesheet"}:
                try:
                    await route.abort()
                except Exception:
                    await route.continue_()
                return

            await route.continue_()

        await page.route("**/*", _route_handler)
    return browser, context, page

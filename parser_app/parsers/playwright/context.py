from __future__ import annotations

from ..config import BROWSER_EXTRA_HEADERS, BROWSER_USER_AGENT


async def create_page(*, browser=None):
    if browser is None:
        raise ValueError("'browser' must be provided")

    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent=BROWSER_USER_AGENT,
        extra_http_headers=dict(BROWSER_EXTRA_HEADERS),
    )
    page = await context.new_page()

    async def _route_handler(route):
        try:
            resource_type = route.request.resource_type
        except Exception:
            resource_type = None

        if resource_type in {"image", "media", "font", "stylesheet"}:
            try:
                await route.abort()
            except Exception:
                await route.continue_()
            return

        await route.continue_()

    await page.route("**/*", _route_handler)
    return browser, context, page

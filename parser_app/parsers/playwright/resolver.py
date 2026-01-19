from __future__ import annotations

import re
from urllib.parse import quote_plus
from urllib.parse import urljoin

from core.exceptions import ParserExecutionError

from ..config import HOME_URL, PRODUCT_URL_PATTERN
from ..utils.overlays import PLAYWRIGHT_OVERLAY_SELECTORS
from .config import PLAYWRIGHT_NAVIGATION_TIMEOUT_MS, PLAYWRIGHT_PRELOADER_TIMEOUT_MS


async def dismiss_overlays(*, page) -> None:
    for selector in PLAYWRIGHT_OVERLAY_SELECTORS:
        try:
            loc = page.locator(selector)
            if await loc.count() < 1:
                continue
            await loc.first.click(timeout=1200, force=True)
        except Exception:
            continue


async def resolve_product_url(*, page, query: str) -> str:
    # Fast path: go directly to search results page.
    search_url = urljoin(HOME_URL, f"/ukr/search/?Search={quote_plus(query)}")
    try:
        await page.goto(
            search_url,
            wait_until="domcontentloaded",
            timeout=PLAYWRIGHT_NAVIGATION_TIMEOUT_MS,
        )
        await page.wait_for_load_state(
            "domcontentloaded",
            timeout=PLAYWRIGHT_NAVIGATION_TIMEOUT_MS,
        )

        # Fastest extraction path: let the browser pick the first matching anchor.
        try:
            href = await page.eval_on_selector(
                "a[href*='-p'][href*='.html']",
                "el => el && el.getAttribute('href')",
            )
            if href and PRODUCT_URL_PATTERN.search(str(href)):
                return urljoin(HOME_URL, str(href))
        except Exception:
            pass

        anchors = page.locator("a[href*='-p'][href*='.html']")
        try:
            await anchors.first.wait_for(state="attached", timeout=20000)
        except Exception:
            pass

        count = await anchors.count()
        for idx in range(min(count, 10)):
            href = await anchors.nth(idx).get_attribute("href")
            if href and PRODUCT_URL_PATTERN.search(href):
                return urljoin(HOME_URL, href)

        # Last resort: tiny HTML scan (kept small by limiting to a short window).
        try:
            html = (await page.content()) or ""
            html = html[:200_000]
            match = re.search(r"href=[\"']([^\"']*-p\d+\.html[^\"']*)[\"']", html)
            if match:
                return urljoin(HOME_URL, match.group(1))
        except Exception:
            pass
    except Exception:
        # Fall back to UI-based resolver below.
        pass

    await page.goto(HOME_URL, wait_until="domcontentloaded", timeout=PLAYWRIGHT_NAVIGATION_TIMEOUT_MS)
    await page.wait_for_load_state("domcontentloaded", timeout=PLAYWRIGHT_NAVIGATION_TIMEOUT_MS)

    try:
        await page.locator("#page-preloader").wait_for(
            state="hidden", timeout=PLAYWRIGHT_PRELOADER_TIMEOUT_MS
        )
    except Exception:
        pass

    await dismiss_overlays(page=page)

    header_input = page.locator("xpath=/html/body/header/div[1]/div/div/div[2]/form/input[1]")
    try:
        await header_input.wait_for(state="visible", timeout=8000)
    except Exception:
        header_input = page.locator(".quick-search-input:visible").first
        await header_input.wait_for(state="attached", timeout=20000)

    try:
        await header_input.scroll_into_view_if_needed(timeout=20000)
    except Exception:
        pass

    try:
        await header_input.click(timeout=20000)
    except Exception:
        await dismiss_overlays(page=page)
        await header_input.click(timeout=20000, force=True)

    search_input = page.locator(".qsr-input:visible").first
    try:
        await search_input.wait_for(state="visible", timeout=5000)
    except Exception:
        search_input = header_input

    try:
        await search_input.fill(query, timeout=20000)
    except Exception:
        await page.evaluate(
            "(sel, value) => {"
            "  const el = document.querySelector(sel);"
            "  if (!el) return;"
            "  el.value = value;"
            "  el.dispatchEvent(new Event('input', { bubbles: true }));"
            "  el.dispatchEvent(new Event('change', { bubbles: true }));"
            "}",
            ".quick-search-input",
            query,
        )

    submitted = False
    for selector in (
        ".qsr-submit:visible",
        ".search-button-first-form:visible",
        "form input[type='submit']:visible",
    ):
        try:
            btn = page.locator(selector).first
            await btn.wait_for(state="visible", timeout=5000)
            await btn.click(timeout=20000)
            submitted = True
            break
        except Exception:
            continue

    if not submitted:
        try:
            await page.keyboard.press("Enter")
        except Exception:
            pass

    try:
        await page.wait_for_load_state("domcontentloaded", timeout=PLAYWRIGHT_NAVIGATION_TIMEOUT_MS)
    except Exception:
        pass

    try:
        await page.wait_for_selector(
            ".qsr-products-list a[href*='-p'][href*='.html'], .qsr-showall",
            timeout=20000,
        )
    except Exception:
        pass

    try:
        show_all = page.locator(".qsr-showall").first
        if await show_all.count() > 0:
            await show_all.click(timeout=20000)
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=PLAYWRIGHT_NAVIGATION_TIMEOUT_MS)
            except Exception:
                pass
    except Exception:
        pass

    for selector in (
        ".qsr-products-list a[href*='-p'][href*='.html']",
        ".qsr-products a[href*='-p'][href*='.html']",
        "a[href*='-p'][href*='.html']",
    ):
        try:
            first = page.locator(selector).first
            await first.wait_for(state="visible", timeout=20000)
            await first.click(timeout=20000)
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=PLAYWRIGHT_NAVIGATION_TIMEOUT_MS)
            except Exception:
                pass
            current_url = page.url
            if current_url and PRODUCT_URL_PATTERN.search(current_url):
                return current_url
        except Exception:
            continue

    current_url = page.url
    if current_url and PRODUCT_URL_PATTERN.search(current_url):
        return current_url

    anchors = page.locator("a[href*='-p'][href*='.html']")
    count = await anchors.count()
    for idx in range(min(count, 30)):
        href = await anchors.nth(idx).get_attribute("href")
        if href and PRODUCT_URL_PATTERN.search(href):
            return urljoin(HOME_URL, href)

    html = (await page.content()) or ""
    match = re.search(r"href=[\"']([^\"']*-p\d+\.html[^\"']*)[\"']", html)
    if match:
        return urljoin(HOME_URL, match.group(1))

    raise ParserExecutionError("Unable to resolve product URL from search results.")

from __future__ import annotations

import re
from urllib.parse import quote_plus
from urllib.parse import urljoin

from core.exceptions import ParserExecutionError

from ..config import HOME_URL, PRODUCT_URL_PATTERN
from ..utils.overlays import PLAYWRIGHT_OVERLAY_SELECTORS
from .config import PLAYWRIGHT_NAVIGATION_TIMEOUT_MS, PLAYWRIGHT_PRELOADER_TIMEOUT_MS


SEARCH_FIRST_PRODUCT_LINK_XPATH = "//a[contains(@href,'-p') and contains(@href,'.html') and normalize-space(string(.))!=''][1]"
HEADER_SEARCH_INPUT_XPATH = "/html/body/header/div[1]/div/div/div[2]/form/input[1]"
HEADER_SEARCH_INPUT_XPATH_FALLBACK = "/html/body/header/div[2]/div/div/div[2]/form/input[1]"
HEADER_SEARCH_SUBMIT_XPATH = "/html/body/header/div[1]/div/div/div[2]/form/input[2]"
HEADER_SEARCH_SUBMIT_XPATH_FALLBACK = "/html/body/header/div[2]/div/div/div[2]/form/input[2]"


async def dismiss_overlays(*, page) -> None:
    for selector in PLAYWRIGHT_OVERLAY_SELECTORS:
        try:
            loc = page.locator(f"xpath={selector}")
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

        anchors = page.locator(f"xpath={SEARCH_FIRST_PRODUCT_LINK_XPATH}")
        try:
            await anchors.first.wait_for(state="attached", timeout=20000)
        except Exception:
            pass
        try:
            href = await anchors.first.get_attribute("href")
            if href and PRODUCT_URL_PATTERN.search(href):
                return urljoin(HOME_URL, href)
        except Exception:
            pass

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
        await page.locator("xpath=//*[@id='page-preloader']").wait_for(
            state="hidden", timeout=PLAYWRIGHT_PRELOADER_TIMEOUT_MS
        )
    except Exception:
        pass

    await dismiss_overlays(page=page)

    header_input = page.locator(f"xpath={HEADER_SEARCH_INPUT_XPATH}")
    try:
        await header_input.wait_for(state="visible", timeout=8000)
    except Exception:
        header_input = page.locator(f"xpath={HEADER_SEARCH_INPUT_XPATH_FALLBACK}")
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

    search_input = header_input

    try:
        await search_input.fill(query, timeout=20000)
    except Exception:
        try:
            await page.evaluate(
                "(xpath, value) => {"
                "  const r = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);"
                "  const el = r.singleNodeValue;"
                "  if (!el) return;"
                "  el.value = value;"
                "  el.dispatchEvent(new Event('input', { bubbles: true }));"
                "  el.dispatchEvent(new Event('change', { bubbles: true }));"
                "}",
                HEADER_SEARCH_INPUT_XPATH,
                query,
            )
        except Exception:
            pass

    submitted = False
    try:
        btn = page.locator(f"xpath={HEADER_SEARCH_SUBMIT_XPATH}")
        await btn.wait_for(state="attached", timeout=5000)
        await btn.click(timeout=20000)
        submitted = True
    except Exception:
        submitted = False

    if not submitted:
        try:
            btn = page.locator(f"xpath={HEADER_SEARCH_SUBMIT_XPATH_FALLBACK}")
            await btn.wait_for(state="attached", timeout=5000)
            await btn.click(timeout=20000)
            submitted = True
        except Exception:
            submitted = False

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
        await page.wait_for_function(
            "() => window.location && window.location.href && window.location.href.includes('/search/')"
        )
    except Exception:
        pass

    try:
        first = page.locator(f"xpath={SEARCH_FIRST_PRODUCT_LINK_XPATH}")
        await first.first.wait_for(state="attached", timeout=20000)
        href = await first.first.get_attribute("href")
        if href and PRODUCT_URL_PATTERN.search(href):
            resolved = urljoin(HOME_URL, href)
            await page.goto(resolved, wait_until="domcontentloaded", timeout=PLAYWRIGHT_NAVIGATION_TIMEOUT_MS)
            await page.wait_for_load_state("domcontentloaded", timeout=PLAYWRIGHT_NAVIGATION_TIMEOUT_MS)
            current_url = page.url
            if current_url and PRODUCT_URL_PATTERN.search(current_url):
                return current_url
            return resolved
    except Exception:
        pass

    current_url = page.url
    if current_url and PRODUCT_URL_PATTERN.search(current_url):
        return current_url

    try:
        html = (await page.content()) or ""
        match = re.search(r"href=[\"']([^\"']*-p\d+\.html[^\"']*)[\"']", html)
        if match:
            return urljoin(HOME_URL, match.group(1))
    except Exception:
        pass

    raise ParserExecutionError("Unable to resolve product URL from search results.")

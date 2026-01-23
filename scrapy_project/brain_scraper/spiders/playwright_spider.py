import os
import sys
from urllib.parse import quote_plus
from urllib.parse import urljoin

import scrapy
from parsel import Selector
from twisted.internet.threads import deferToThread

from core.enums import ParserType
from parser_app.common.constants import (
    ALL_CHARACTERISTICS_BUTTON_XPATH,
    DEFAULT_QUERY,
    HOME_SEARCH_INPUT_XPATH,
    HOME_SEARCH_INPUT_XPATH_FALLBACK,
    HOME_SEARCH_SUBMIT_XPATH,
    HOME_SEARCH_SUBMIT_XPATH_FALLBACK,
    HOME_URL,
    PRODUCT_CODE_XPATH,
    SEARCH_FIRST_PRODUCT_LINK_XPATH,
)
from parser_app.serializers import ProductScrapeRequestSerializer

from .base import extract_product_item


def _playwright_job(*, query: str) -> tuple[str, str]:
    import asyncio
    from playwright.sync_api import ViewportSize, sync_playwright

    if sys.platform.startswith("win"):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--disable-dev-shm-usage", "--blink-settings=imagesEnabled=false"])
        viewport: ViewportSize = {"width": 1920, "height": 1080}
        context = browser.new_context(viewport=viewport)
        page = context.new_page()

        def _route_handler(route):
            try:
                resource_type = route.request.resource_type
            except Exception:
                resource_type = None
            if resource_type in {"image", "media", "font", "stylesheet"}:
                try:
                    route.abort()
                except Exception:
                    route.continue_()
                return
            route.continue_()

        page.route("**/*", _route_handler)

        try:
            page.goto(HOME_URL, wait_until="domcontentloaded", timeout=60000)

            pairs = [
                (HOME_SEARCH_INPUT_XPATH_FALLBACK, HOME_SEARCH_SUBMIT_XPATH_FALLBACK),
                (HOME_SEARCH_INPUT_XPATH, HOME_SEARCH_SUBMIT_XPATH),
            ]
            input_xpath, submit_xpath = HOME_SEARCH_INPUT_XPATH, HOME_SEARCH_SUBMIT_XPATH
            for ix, sx in pairs:
                try:
                    loc = page.locator(f"xpath={ix}").first
                    if loc.count() > 0 and loc.is_visible():
                        input_xpath, submit_xpath = ix, sx
                        break
                except Exception:
                    continue

            page.wait_for_selector(f"xpath={input_xpath}", timeout=20000)
            page.locator(f"xpath={input_xpath}").fill(query, timeout=20000)
            try:
                page.keyboard.press("Enter")
            except Exception:
                pass

            # Best-effort fallback: force click with a short timeout to avoid hanging on interceptors.
            try:
                page.locator(f"xpath={submit_xpath}").first.click(timeout=2000, force=True)
            except Exception:
                pass

            search_url = f"https://brain.com.ua/ukr/search/?Search={quote_plus(query)}"
            try:
                page.wait_for_url("**/search/**", timeout=15000)
            except Exception:
                page.goto(search_url, wait_until="domcontentloaded", timeout=60000)

            page.wait_for_selector(f"xpath={SEARCH_FIRST_PRODUCT_LINK_XPATH}", timeout=30000, state="attached")

            # Avoid click interception by preloader/overlays: resolve href and navigate directly.
            first_link = page.locator(f"xpath={SEARCH_FIRST_PRODUCT_LINK_XPATH}").first
            href = None
            try:
                href = first_link.get_attribute("href")
            except Exception:
                href = None

            if href:
                try:
                    page.wait_for_selector("css=#page-preloader", state="hidden", timeout=5000)
                except Exception:
                    pass
                page.goto(urljoin(page.url, href), wait_until="domcontentloaded", timeout=60000)
            else:
                try:
                    first_link.click(timeout=2000, force=True)
                except Exception:
                    pass

            page.wait_for_selector(f"xpath={PRODUCT_CODE_XPATH}", timeout=30000, state="attached")

            try:
                btn = page.locator(f"xpath={ALL_CHARACTERISTICS_BUTTON_XPATH}").first
                if btn.count() > 0:
                    try:
                        btn.scroll_into_view_if_needed(timeout=5000)
                    except Exception:
                        pass
                    try:
                        btn.click(timeout=5000)
                    except Exception:
                        pass
            except Exception:
                pass

            source_url = page.url
            html = page.content()
            return source_url, html
        finally:
            try:
                context.close()
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass


class BrainPlaywrightSpider(scrapy.Spider):
    name = "brain_playwright"

    custom_settings = {
        "DOWNLOAD_DELAY": float(os.getenv("SCRAPY_PLAYWRIGHT_DOWNLOAD_DELAY", "0.5")),
        "CONCURRENT_REQUESTS": int(os.getenv("SCRAPY_PLAYWRIGHT_CONCURRENT_REQUESTS", "1")),
        "CLOSESPIDER_TIMEOUT": int(os.getenv("SCRAPY_PLAYWRIGHT_CLOSESPIDER_TIMEOUT", "120")),
    }

    def __init__(self, query: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        defaults = ProductScrapeRequestSerializer.get_default_payload(ParserType.PLAYWRIGHT.value)
        self.query = query or defaults.get("query") or DEFAULT_QUERY

    def start_requests(self):
        yield scrapy.Request(HOME_URL, callback=self.parse, dont_filter=True)

    def parse(self, response: scrapy.http.Response):
        d = deferToThread(_playwright_job, query=self.query)

        def _on_success(result):
            source_url, html = result
            selector = Selector(text=html)
            item = extract_product_item(
                selector=selector,
                source_url=source_url,
                metadata={"parser": "ScrapyPlaywright", "query": self.query},
            )
            return [item]

        def _on_error(failure):
            self.logger.error("Playwright spider error: %s", failure)
            return []

        d.addCallback(_on_success)
        d.addErrback(_on_error)
        return d

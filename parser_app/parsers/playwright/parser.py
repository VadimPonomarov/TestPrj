import re
from urllib.parse import urljoin
from typing import Optional

from core.exceptions import ParserExecutionError
from core.schemas import ProductData
from ..base.parser import BaseBrainParser
from ..utils.cache import get_cached_url, set_cached_url

# Import from the existing parsers package
from ...services.parsers import BrainProductParser


class PlaywrightBrainParser(BaseBrainParser):
    """Parser implementation using Playwright for JavaScript-heavy pages."""

    HOME_URL = "https://brain.com.ua/"
    PRODUCT_URL_PATTERN = re.compile(r"-p\d+\.html(?:$|\?)")

    SCRAPE_HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Referer": "https://www.google.com/",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
        "DNT": "1",
    }

    def _parse(self, *, query: Optional[str], url: Optional[str]) -> ProductData:
        resolved_url = url

        cached_url = get_cached_url("playwright", query)
        if not resolved_url and cached_url:
            resolved_url = cached_url

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=self.SCRAPE_HEADERS.get("User-Agent"),
                    extra_http_headers={
                        k: v for k, v in self.SCRAPE_HEADERS.items() if k != "User-Agent"
                    },
                )
                page = context.new_page()

                try:
                    if query and not resolved_url:
                        resolved_url = self._resolve_product_url(page=page, query=query)

                    if resolved_url and query:
                        set_cached_url("playwright", query, resolved_url)

                    if not resolved_url:
                        raise ParserExecutionError(
                            "Either 'query' or 'url' must be provided for the Playwright parser."
                        )

                    page.goto(resolved_url, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_load_state("load", timeout=60000)

                    content = page.content()

                    # Reuse BrainProductParser with the already fetched HTML to avoid extra requests
                    parser = BrainProductParser(resolved_url, html=content)
                    raw_payload = parser.parse()

                    if not raw_payload:
                        raise ParserExecutionError("No data returned from Playwright parser.")

                    product = ProductData.from_mapping(raw_payload)
                    product.source_url = resolved_url
                    return product

                finally:
                    context.close()
                    browser.close()

        except ImportError:
            raise ParserExecutionError("Playwright is not installed. Please install it with 'pip install playwright' and run 'playwright install'")
        except Exception as e:
            msg = str(e) or repr(e)
            raise ParserExecutionError(f"Error during Playwright parsing: {msg}")

    def _dismiss_overlays(self, *, page) -> None:
        selectors = [
            "button.cookie__agree",
            "button.cookie-agree",
            "button#cookie-accept",
            "button:has-text('Приймаю')",
            "button:has-text('Принять')",
            "button:has-text('Accept')",
            "button:has-text('OK')",
            ".modal__close",
            ".popup-close",
            "[aria-label='Close']",
            ".fancybox-close",
        ]

        for selector in selectors:
            try:
                loc = page.locator(selector)
                if loc.count() < 1:
                    continue
                loc.first.click(timeout=1200, force=True)
            except Exception:
                continue

    def _resolve_product_url(self, *, page, query: str) -> str:
        page.goto(self.HOME_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_load_state("load", timeout=60000)

        try:
            page.locator("#page-preloader").wait_for(state="hidden", timeout=20000)
        except Exception:
            pass

        self._dismiss_overlays(page=page)

        # Step-2: focus search on homepage
        header_input = page.locator(
            "xpath=/html/body/header/div[1]/div/div/div[2]/form/input[1]"
        )
        try:
            header_input.wait_for(state="visible", timeout=8000)
        except Exception:
            header_input = page.locator(".quick-search-input:visible").first
            header_input.wait_for(state="attached", timeout=20000)
        try:
            header_input.scroll_into_view_if_needed(timeout=20000)
        except Exception:
            pass

        try:
            header_input.click(timeout=20000)
        except Exception:
            self._dismiss_overlays(page=page)
            header_input.click(timeout=20000, force=True)

        # Prefer qsr-input (paired with a visible submit "Знайти")
        search_input = page.locator(".qsr-input:visible").first
        try:
            search_input.wait_for(state="visible", timeout=5000)
        except Exception:
            search_input = header_input

        try:
            search_input.fill(query, timeout=20000)
        except Exception:
            page.evaluate(
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

        # Step-3: click submit ("Знайти")
        submitted = False
        for selector in (
            ".qsr-submit:visible",
            ".search-button-first-form:visible",
            "form input[type='submit']:visible",
        ):
            try:
                btn = page.locator(selector).first
                btn.wait_for(state="visible", timeout=5000)
                btn.click(timeout=20000)
                submitted = True
                break
            except Exception:
                continue

        if not submitted:
            try:
                page.keyboard.press("Enter")
            except Exception:
                pass

        try:
            page.wait_for_load_state("load", timeout=60000)
        except Exception:
            pass

        # Wait for quick-search products list or the "show all" link.
        try:
            page.wait_for_selector(
                ".qsr-products-list a[href*='-p'][href*='.html'], .qsr-showall",
                timeout=20000,
            )
        except Exception:
            pass

        # If only show-all is present, click it to navigate to full results page.
        try:
            show_all = page.locator(".qsr-showall").first
            if show_all.count() > 0:
                show_all.click(timeout=20000)
                try:
                    page.wait_for_load_state("load", timeout=60000)
                except Exception:
                    pass
        except Exception:
            pass

        # Step-4: click first product in results
        for selector in (
            ".qsr-products-list a[href*='-p'][href*='.html']",
            ".qsr-products a[href*='-p'][href*='.html']",
            "a[href*='-p'][href*='.html']",
        ):
            try:
                first = page.locator(selector).first
                first.wait_for(state="visible", timeout=20000)
                first.click(timeout=20000)
                try:
                    page.wait_for_load_state("load", timeout=60000)
                except Exception:
                    pass
                current_url = page.url
                if current_url and self.PRODUCT_URL_PATTERN.search(current_url):
                    return current_url
            except Exception:
                continue

        current_url = page.url
        if current_url and self.PRODUCT_URL_PATTERN.search(current_url):
            return current_url

        anchors = page.locator("a[href*='-p'][href*='.html']")
        count = anchors.count()
        for idx in range(min(count, 30)):
            href = anchors.nth(idx).get_attribute("href")
            if href and self.PRODUCT_URL_PATTERN.search(href):
                return urljoin(self.HOME_URL, href)

        html = page.content() or ""
        match = re.search(r'href=["\']([^"\']*-p\d+\.html[^"\']*)["\']', html)
        if match:
            return urljoin(self.HOME_URL, match.group(1))

        raise ParserExecutionError("Unable to resolve product URL from search results.")


# Backwards-compatible alias for package exports expecting PlaywrightParser
PlaywrightParser = PlaywrightBrainParser

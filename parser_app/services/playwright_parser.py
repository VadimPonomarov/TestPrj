import os
from typing import Optional, Sequence, Tuple
from urllib.parse import urljoin

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    Response,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from core.exceptions import ParserExecutionError
from core.schemas import ProductData

from .base import BaseBrainParser
from .brain_parser import BrainProductParser


class PlaywrightBrainParser(BaseBrainParser):
    """Playwright-based implementation for brain.com.ua."""

    BASE_URL = "https://brain.com.ua/"
    SEARCH_INPUT_SELECTORS: Sequence[str] = (
        "/html/body/header/div[1]/div/div/div[2]/form/input[1]",  # Exact XPath provided by user
        "//input[contains(@class, 'quick-search-input')]",  # Header search input on homepage
        "//input[contains(@class, 'header-search__input')]",  # Legacy selector
        "//form[contains(@class, 'header-search')]//input[@type='text']",  # XPath for input type
        "input.quick-search-input",
        "input[name='search']",
        "input[type='search']",
        "input.header-search__input",
    )
    SEARCH_BUTTON_SELECTORS: Sequence[str] = (
        "input.search-button-first-form",
        "input.qsr-submit",
        "input[type='submit']",
        "button[type='submit']",
        "button.header-search__submit",
        "button.search-form__submit",
    )
    RESULT_LINK_SELECTORS: Sequence[str] = (
        "a.product-card__title",
        "a.product-name",
        "a.product-item__title",
        "a.catalog-item__title",
        "a[href*='/product/']",
    )
    PRODUCT_READY_SELECTORS: Sequence[str] = (
        "script[type='application/ld+json']",
        "div.product",
    )

    def __init__(self, *, headless: bool = True) -> None:
        super().__init__()
        self.headless = headless

    def _parse(self, *, query: Optional[str], url: Optional[str]) -> ProductData:
        with sync_playwright() as playwright:
            browser = self._launch_browser(playwright)
            try:
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    ),
                    locale="uk-UA",
                    viewport={"width": 1920, "height": 1080},
                    extra_http_headers={
                        "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
                    },
                )
                page = context.new_page()

                # Поведение по ТЗ:
                # - если есть query → сценарий поиска (Шаг-1..4)
                # - если url == BASE_URL и query нет → тоже сценарий поиска
                # - если url является прямой ссылкой на товар → сразу открываем её

                if query:
                    page, target_url = self._process_query(page, query)
                elif url:
                    if url.rstrip("/") == self.BASE_URL.rstrip("/"):
                        # Пользователь передал главную, запускаем сценарий поиска.
                        default_query = "Apple iPhone 15 128GB Black"
                        page, target_url = self._process_query(page, default_query)
                    else:
                        target_url = url
                        self._navigate_with_retry(page, target_url)
                        self._wait_for_navigation(page)
                else:  # pragma: no cover - guarded by BaseBrainParser
                    raise ParserExecutionError(
                        "Either 'query' must be provided (for search flow) or 'url' must point to a product page."
                    )

                self._wait_for_product_page(page)
                page_html = page.content()
            finally:
                browser.close()

        parser = BrainProductParser(target_url, html=page_html)
        payload = parser.parse()
        if not payload:
            raise ParserExecutionError("Failed to extract product data from Playwright session.")

        product = ProductData.from_mapping(payload)
        product.source_url = target_url
        return product

    def _launch_browser(self, playwright: Playwright) -> Browser:
        proxy_server = os.getenv("PLAYWRIGHT_PROXY_SERVER")
        proxy_username = os.getenv("PLAYWRIGHT_PROXY_USERNAME")
        proxy_password = os.getenv("PLAYWRIGHT_PROXY_PASSWORD")

        launch_kwargs = {
            "headless": self.headless,
            "args": ["--disable-gpu", "--no-sandbox"],
        }

        if proxy_server:
            proxy_config = {"server": proxy_server}
            if proxy_username:
                proxy_config["username"] = proxy_username
            if proxy_password:
                proxy_config["password"] = proxy_password
            launch_kwargs["proxy"] = proxy_config

        return playwright.chromium.launch(**launch_kwargs)

    def _process_query(self, page: Page, query: str) -> Tuple[Page, str]:
        self._navigate_with_retry(page, self.BASE_URL)

        search_input = self._query_first(page, self.SEARCH_INPUT_SELECTORS)
        search_input.fill("")
        search_input.type(query)

        submit_button = self._query_first(page, self.SEARCH_BUTTON_SELECTORS)
        submit_button.click()

        self._wait_for_results(page)
        first_link = self._query_first(page, self.RESULT_LINK_SELECTORS)
        href = first_link.get_attribute("href")
        if not href:
            raise ParserExecutionError("Search result link does not contain href attribute.")

        target_url = href if href.startswith("http") else urljoin(self.BASE_URL, href)
        self._navigate_with_retry(page, target_url)
        self._wait_for_navigation(page)
        self._wait_for_product_page(page)
        return page, target_url

    def _query_first(self, page: Page, selectors: Sequence[str]):
        last_error: Optional[Exception] = None
        for selector in selectors:
            try:
                # Ждём именно видимый и интерактивный элемент, чтобы fill() не падал по timeout.
                handle = page.wait_for_selector(selector, state="visible", timeout=30000)
                if handle:
                    return handle
            except Exception as exc:
                last_error = exc
                continue

        raise ParserExecutionError(
            f"Failed to locate a visible element using selectors: {selectors}. Last error: {last_error}"
        )

    def _wait_for_results(self, page: Page) -> None:
        try:
            page.wait_for_selector(
                ", ".join(self.RESULT_LINK_SELECTORS),
                timeout=15000,
                state="attached",
            )
        except Exception as exc:
            raise ParserExecutionError("Search results did not load in time.") from exc

    def _wait_for_navigation(self, page: Page) -> None:
        page.wait_for_load_state("domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            page.wait_for_timeout(2000)

    def _wait_for_product_page(self, page: Page) -> None:
        self._raise_if_cloudflare(page)

        # BrainProductParser primarily needs JSON-LD, so wait for it first.
        try:
            page.wait_for_function(
                "() => !!document.querySelector('script[type=\"application/ld+json\"]')",
                timeout=45000,
            )
            return
        except PlaywrightTimeoutError:
            pass

        for selector in self.PRODUCT_READY_SELECTORS:
            try:
                page.wait_for_selector(selector, timeout=20000)
                return
            except Exception:
                continue

        # Fallback: give the page a short grace period and retry once
        page.wait_for_timeout(3000)
        for selector in self.PRODUCT_READY_SELECTORS:
            try:
                page.wait_for_selector(selector, timeout=5000)
                return
            except Exception:
                continue

        title: str = ""
        try:
            title = page.title()
        except Exception:
            pass

        snippet: str = ""
        try:
            snippet = page.content()[:1500]
        except Exception:
            pass

        self.logger.error(
            "Product page did not become ready in time. url=%s title=%s snippet=%s",
            page.url,
            title,
            snippet,
        )

        raise ParserExecutionError("Product page did not load in time.")

    def _navigate_with_retry(self, page: Page, url: str, *, attempts: int = 2) -> None:
        last_error: Optional[Exception] = None
        for attempt in range(1, attempts + 1):
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=45000)
                self._raise_if_bad_response(page, response, url)
                return
            except Exception as exc:
                last_error = exc
                self.logger.warning("Playwright navigation attempt %s failed: %s", attempt, exc)
                page.wait_for_timeout(2000)

        raise ParserExecutionError(f"Failed to navigate to {url}: {last_error}")

    def _raise_if_bad_response(self, page: Page, response: Optional[Response], url: str) -> None:
        if response is not None and response.status >= 400:
            raise ParserExecutionError(
                f"HTTP {response.status} while navigating to {url}. "
                "This often indicates Cloudflare or network blocking from the container."
            )

        self._raise_if_cloudflare(page)

    def _raise_if_cloudflare(self, page: Page) -> None:
        title = ""
        try:
            title = page.title() or ""
        except Exception:
            title = ""

        if "cloudflare" in title.lower():
            raise ParserExecutionError(
                "Cloudflare protection page detected (title contains 'cloudflare'). "
                "Try running from a different IP/proxy (PLAYWRIGHT_PROXY_SERVER)."
            )

        snippet = ""
        try:
            snippet = (page.content() or "")[:5000].lower()
        except Exception:
            snippet = ""

        markers = (
            "cloudflare",
            "cf-error",
            "error 502",
            "attention required",
            "checking your browser",
            "ray id",
        )
        if any(marker in snippet for marker in markers):
            raise ParserExecutionError(
                "Cloudflare/edge error page detected instead of product page. "
                "Most likely your container IP is blocked. Use proxy (PLAYWRIGHT_PROXY_SERVER) "
                "or run scraping outside Docker."
            )


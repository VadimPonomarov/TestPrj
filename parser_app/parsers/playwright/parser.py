import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
 
from core.exceptions import ParserExecutionError
from core.schemas import ProductData
from ..base.parser import BaseBrainParser
from ..utils.cache import get_cached_url, set_cached_url
from ..utils.product import build_product_data
from .config import PLAYWRIGHT_NAVIGATION_TIMEOUT_MS
from .context import create_page
from .resolver import resolve_product_url
from .runtime import get_browser as get_reused_browser
from .runtime import is_reuse_enabled as is_browser_reuse_enabled


class PlaywrightBrainParser(BaseBrainParser):
    """Parser implementation using Playwright for JavaScript-heavy pages."""
 
    CACHE_KEY = "playwright"

    def _parse(self, *, query: Optional[str], url: Optional[str]) -> ProductData:
        resolved_url = url

        if resolved_url and not query:
            return build_product_data(url=resolved_url, parser_label="Playwright")
        cached_url = get_cached_url(self.CACHE_KEY, query)
        if not resolved_url and cached_url:
            return build_product_data(url=cached_url, parser_label="Playwright")
 
        try:
            browser_reuse = is_browser_reuse_enabled()
 
            if browser_reuse:
                browser = get_reused_browser()
                browser, context, page = create_page(browser=browser)
                try:
                    if query and not resolved_url:
                        resolved_url = resolve_product_url(page=page, query=query)

                    if resolved_url and query:
                        set_cached_url(self.CACHE_KEY, query, resolved_url)

                    if not resolved_url:
                        raise ParserExecutionError(
                            "Either 'query' or 'url' must be provided for the Playwright parser."
                        )

                    already_on_url = False
                    try:
                        already_on_url = page.url == resolved_url
                    except Exception:
                        already_on_url = False

                    if not already_on_url:
                        page.goto(
                            resolved_url,
                            wait_until="domcontentloaded",
                            timeout=PLAYWRIGHT_NAVIGATION_TIMEOUT_MS,
                        )

                    page.wait_for_load_state(
                        "domcontentloaded",
                        timeout=PLAYWRIGHT_NAVIGATION_TIMEOUT_MS,
                    )
                    try:
                        page.wait_for_selector(
                            "script[type='application/ld+json']",
                            timeout=8000,
                        )
                    except Exception:
                        pass

                    content = page.content()
                    return build_product_data(
                        url=resolved_url,
                        html=content,
                        parser_label="Playwright",
                    )

                finally:
                    try:
                        context.close()
                    except Exception:
                        pass

            else:
                def _run_sync_playwright() -> ProductData:
                    nonlocal resolved_url
                    from playwright.sync_api import sync_playwright

                    with sync_playwright() as p:
                        browser, context, page = create_page(playwright=p)
                        try:
                            if query and not resolved_url:
                                resolved_url = resolve_product_url(page=page, query=query)

                            if resolved_url and query:
                                set_cached_url(self.CACHE_KEY, query, resolved_url)

                            if not resolved_url:
                                raise ParserExecutionError(
                                    "Either 'query' or 'url' must be provided for the Playwright parser."
                                )

                            already_on_url = False
                            try:
                                already_on_url = page.url == resolved_url
                            except Exception:
                                already_on_url = False

                            if not already_on_url:
                                page.goto(
                                    resolved_url,
                                    wait_until="domcontentloaded",
                                    timeout=PLAYWRIGHT_NAVIGATION_TIMEOUT_MS,
                                )

                            page.wait_for_load_state(
                                "domcontentloaded",
                                timeout=PLAYWRIGHT_NAVIGATION_TIMEOUT_MS,
                            )
                            try:
                                page.wait_for_selector(
                                    "script[type='application/ld+json']",
                                    timeout=8000,
                                )
                            except Exception:
                                pass

                            content = page.content()
                            return build_product_data(
                                url=resolved_url,
                                html=content,
                                parser_label="Playwright",
                            )

                        finally:
                            try:
                                context.close()
                            except Exception:
                                pass
                            try:
                                browser.close()
                            except Exception:
                                pass

                loop_running = False
                try:
                    asyncio.get_running_loop()
                    loop_running = True
                except RuntimeError:
                    loop_running = False

                if loop_running:
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        return executor.submit(_run_sync_playwright).result()
                return _run_sync_playwright()

        except ImportError:
            raise ParserExecutionError("Playwright is not installed. Please install it with 'pip install playwright' and run 'playwright install'")
        except Exception as e:
            msg = str(e) or repr(e)
            raise ParserExecutionError(f"Error during Playwright parsing: {msg}")

# Backwards-compatible alias for package exports expecting PlaywrightParser
PlaywrightParser = PlaywrightBrainParser

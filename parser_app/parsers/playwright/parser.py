from typing import Optional
import os
 
from core.exceptions import ParserExecutionError
from core.schemas import ProductData
from ..base.parser import BaseBrainParser
from ..utils.cache import get_cached_url, set_cached_url
from ..utils.product import build_product_data
from .config import PLAYWRIGHT_NAVIGATION_TIMEOUT_MS
from .context import create_page
from .resolver import resolve_product_url
from .runtime import run_in_browser_thread


class PlaywrightBrainParser(BaseBrainParser):
    """Parser implementation using Playwright for JavaScript-heavy pages."""
 
    CACHE_KEY = "playwright"

    @staticmethod
    def _query_cache_enabled() -> bool:
        raw = os.getenv("PLAYWRIGHT_QUERY_CACHE_ENABLED", "").strip()
        if raw == "":
            return True
        return raw in {"1", "true", "True", "yes", "YES"}

    def _parse(self, *, query: Optional[str], url: Optional[str]) -> ProductData:
        resolved_url = url

        if resolved_url and not query:
            return build_product_data(url=resolved_url, parser_label="Playwright")
        cached_url = get_cached_url(self.CACHE_KEY, query) if self._query_cache_enabled() else None
        if not resolved_url and cached_url:
            return build_product_data(url=cached_url, parser_label="Playwright")
 
        try:
            async def _job(browser):
                nonlocal resolved_url

                _, context, page = await create_page(browser=browser)
                try:
                    if query and not resolved_url:
                        resolved_url = await resolve_product_url(page=page, query=query)

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
                        response = await page.goto(
                            resolved_url,
                            wait_until="domcontentloaded",
                            timeout=PLAYWRIGHT_NAVIGATION_TIMEOUT_MS,
                        )
                    else:
                        response = None

                    # Avoid extra waits; prefer raw response HTML which is typically faster than DOM serialization.
                    content = None
                    if response is not None:
                        try:
                            content = await response.text()
                        except Exception:
                            content = None
                    if not content:
                        content = await page.content()
                    return resolved_url, content
                finally:
                    try:
                        await context.close()
                    except Exception:
                        pass

            resolved_url, content = run_in_browser_thread(_job)
            if resolved_url and query:
                if self._query_cache_enabled():
                    set_cached_url(self.CACHE_KEY, query, resolved_url)

            try:
                return build_product_data(
                    url=resolved_url,
                    html=content,
                    parser_label="Playwright",
                )
            except ParserExecutionError:
                return build_product_data(
                    url=resolved_url,
                    parser_label="Playwright",
                )

        except ImportError:
            raise ParserExecutionError(
                "Playwright is not installed. Please install it with 'pip install playwright' and run 'playwright install'"
            )
        except Exception as e:
            msg = str(e) or repr(e)
            raise ParserExecutionError(f"Error during Playwright parsing: {msg}")

# Backwards-compatible alias for package exports expecting PlaywrightParser
PlaywrightParser = PlaywrightBrainParser

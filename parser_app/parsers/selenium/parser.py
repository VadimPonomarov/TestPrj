from typing import Optional
import os
 
from core.exceptions import ParserExecutionError
from core.schemas import ProductData
from ..base.parser import BaseBrainParser
from ..utils.cache import get_cached_url, set_cached_url
from ..utils.product import build_product_data
from .driver import apply_headers, create_driver
from .resolver import resolve_product_url
from .runtime import get_driver as get_reused_driver
from .runtime import is_reuse_enabled as is_driver_reuse_enabled
from .runtime import reset_driver_state


class SeleniumBrainParser(BaseBrainParser):
    """Parser implementation using Selenium for JavaScript-heavy pages."""

    CACHE_KEY = "selenium"

    @staticmethod
    def _query_cache_enabled() -> bool:
        raw = os.getenv("SELENIUM_QUERY_CACHE_ENABLED", "").strip()
        if raw == "":
            return True
        return raw in {"1", "true", "True", "yes", "YES"}
    
    def _parse(self, *, query: Optional[str] = None, url: Optional[str] = None) -> ProductData:
        if not query and url:
            return build_product_data(url=url, parser_label="Selenium")

        cached_url = get_cached_url(self.CACHE_KEY, query) if self._query_cache_enabled() else None
        if cached_url:
            try:
                return build_product_data(url=cached_url, parser_label="Selenium")
            except ParserExecutionError:
                pass

        driver_reuse = is_driver_reuse_enabled()
        if driver_reuse:
            try:
                driver = get_reused_driver()
                reset_driver_state(driver=driver)
            except Exception as exc:
                raise ParserExecutionError(str(exc)) from exc
        else:
            try:
                driver = create_driver()
            except ImportError:
                raise ParserExecutionError(
                    "Selenium dependencies not found. Please install with: pip install selenium"
                )

        try:
            if not driver_reuse:
                apply_headers(driver=driver)
            resolved_url = resolve_product_url(
                driver=driver,
                query=query,
                url=url,
                logger=self.logger,
            )

            try:
                current_url = getattr(driver, "current_url", "") or ""
            except Exception:
                current_url = ""

            if resolved_url and current_url != resolved_url:
                try:
                    from selenium.webdriver.support.ui import WebDriverWait
                    from selenium.webdriver.support import expected_conditions as EC
                    from selenium.webdriver.common.by import By

                    driver.get(resolved_url)
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.XPATH, "//body"))
                    )
                except Exception:
                    try:
                        driver.get(resolved_url)
                    except Exception:
                        pass

            if self._query_cache_enabled():
                set_cached_url(self.CACHE_KEY, query, resolved_url)
            html = getattr(driver, "page_source", None) or None
            return build_product_data(url=resolved_url, html=html, parser_label="Selenium")

        except Exception as e:
            self.logger.error(f"Error during Selenium parsing: {str(e)}")
            raise ParserExecutionError(f"Failed to parse product: {str(e)}")

        finally:
            if not driver_reuse:
                try:
                    driver.quit()
                except Exception:
                    pass

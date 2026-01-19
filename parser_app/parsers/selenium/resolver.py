from __future__ import annotations

import os
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus
from urllib.parse import urljoin

from core.exceptions import ParserExecutionError

from ..config import HOME_URL, PRODUCT_URL_PATTERN
from ..utils.overlays import SELENIUM_OVERLAY_SELECTORS
from .config import (
    HEADER_SEARCH_INPUT_XPATH,
    HEADER_SEARCH_SUBMIT_XPATH,
    SELENIUM_WAIT_TIMEOUT_SECONDS,
)


def _dump_debug_html(*, driver, logger, label: str) -> None:
    try:
        base_dir = os.path.join(os.getcwd(), "temp")
        os.makedirs(base_dir, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(base_dir, f"selenium_debug_{label}_{timestamp}.html")
        html = driver.page_source or ""
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        logger.error("Saved Selenium debug HTML to %s", path)
    except Exception:
        return


def _first_visible_by_css(*, driver, By, selector: str):
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
    except Exception:
        return None
    for el in elements:
        try:
            if el.is_displayed() and el.is_enabled():
                return el
        except Exception:
            continue
    return None


def _safe_click(*, driver, element) -> bool:
    if element is None:
        return False
    try:
        element.click()
        return True
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", element)
            return True
        except Exception:
            return False


def _dismiss_overlays(*, driver, By) -> None:
    for selector in SELENIUM_OVERLAY_SELECTORS:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if not elements:
                continue
            el = elements[0]
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
            except Exception:
                pass
            try:
                el.click()
            except Exception:
                try:
                    driver.execute_script("arguments[0].click();", el)
                except Exception:
                    pass
        except Exception:
            continue


def resolve_product_url(*, driver, query: Optional[str], url: Optional[str], logger) -> str:
    if query:
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        wait = WebDriverWait(driver, SELENIUM_WAIT_TIMEOUT_SECONDS)
        stage = "open_home"
        try:
            stage = "open_search"
            try:
                search_url = urljoin(HOME_URL, f"/ukr/search/?Search={quote_plus(query)}")
                driver.get(search_url)
                try:
                    wait.until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "a[href*='-p'][href*='.html']")
                        )
                    )
                except Exception:
                    pass

                try:
                    first = driver.find_element(By.CSS_SELECTOR, "a[href*='-p'][href*='.html']")
                    href = first.get_attribute("href")
                    if href and PRODUCT_URL_PATTERN.search(href):
                        return href
                except Exception:
                    pass
            except Exception:
                pass

            stage = "open_home"
            driver.get(HOME_URL)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

            stage = "wait_preloader"
            try:
                wait.until(EC.invisibility_of_element_located((By.ID, "page-preloader")))
            except Exception:
                pass

            stage = "dismiss_overlays"
            _dismiss_overlays(driver=driver, By=By)

            stage = "focus_search_input"
            header_input = None
            try:
                candidate = driver.find_element(By.XPATH, HEADER_SEARCH_INPUT_XPATH)
                if candidate.is_displayed() and candidate.is_enabled():
                    header_input = candidate
            except Exception:
                header_input = None

            if header_input is None:
                header_input = _first_visible_by_css(driver=driver, By=By, selector=".quick-search-input")
            if header_input is None:
                header_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".quick-search-input")))

            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", header_input)
            except Exception:
                pass

            if not _safe_click(driver=driver, element=header_input):
                raise ParserExecutionError("Unable to focus search input.")

            stage = "wait_qsr_block"
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".qsr-block")))
            except Exception:
                pass

            stage = "obtain_search_input"
            search_input = _first_visible_by_css(driver=driver, By=By, selector=".qsr-input")
            if search_input is None:
                search_input = header_input

            stage = "fill_search_input"
            try:
                search_input.send_keys(Keys.CONTROL, "a")
                search_input.send_keys(Keys.BACKSPACE)
            except Exception:
                pass
            search_input.send_keys(query)

            stage = "submit_search"
            submitted = False
            try:
                btn = driver.find_element(By.XPATH, HEADER_SEARCH_SUBMIT_XPATH)
                submitted = _safe_click(driver=driver, element=btn)
            except Exception:
                submitted = False
            if not submitted:
                for selector in (
                    ".qsr-submit",
                    ".search-button-first-form",
                    "form input[type='submit']",
                ):
                    btn = _first_visible_by_css(driver=driver, By=By, selector=selector)
                    if btn and _safe_click(driver=driver, element=btn):
                        submitted = True
                        break
            if not submitted:
                try:
                    search_input.send_keys(Keys.ENTER)
                except Exception:
                    pass

            stage = "wait_results"
            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".qsr-products-list a[href*='-p'][href*='.html'], .qsr-showall")
                    )
                )
            except Exception:
                pass

            stage = "click_showall"
            try:
                show_all = _first_visible_by_css(driver=driver, By=By, selector=".qsr-showall")
                if show_all is not None:
                    _safe_click(driver=driver, element=show_all)
            except Exception:
                pass

            stage = "open_first_product"
            for selector in (
                ".qsr-products-list a[href*='-p'][href*='.html']",
                ".qsr-products a[href*='-p'][href*='.html']",
                "a[href*='-p'][href*='.html']",
            ):
                first = _first_visible_by_css(driver=driver, By=By, selector=selector)
                if first is None:
                    continue
                href = None
                try:
                    href = first.get_attribute("href")
                except Exception:
                    href = None
                if _safe_click(driver=driver, element=first):
                    try:
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
                    except Exception:
                        pass
                    current = getattr(driver, "current_url", "") or ""
                    if current and PRODUCT_URL_PATTERN.search(current):
                        return current
                if href and PRODUCT_URL_PATTERN.search(href):
                    return href

            current = getattr(driver, "current_url", "") or ""
            if current and PRODUCT_URL_PATTERN.search(current):
                return current

            raise ParserExecutionError("Unable to resolve product URL from search results.")
        except Exception as exc:
            _dump_debug_html(driver=driver, logger=logger, label=f"resolve_{stage}")
            msg = getattr(exc, "msg", None) or str(exc) or repr(exc)
            raise ParserExecutionError(f"{stage}: {msg}") from exc

    if not url:
        raise ParserExecutionError("Either 'query' or 'url' must be provided.")
    return url

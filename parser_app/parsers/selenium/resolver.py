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


SEARCH_FIRST_PRODUCT_LINK_XPATH = "//a[contains(@href,'-p') and contains(@href,'.html') and normalize-space(string(.))!=''][1]"
HEADER_SEARCH_INPUT_XPATH_FALLBACK = "/html/body/header/div[2]/div/div/div[2]/form/input[1]"
HEADER_SEARCH_SUBMIT_XPATH_FALLBACK = "/html/body/header/div[2]/div/div/div[2]/form/input[2]"


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


def _first_visible_by_xpath(*, driver, By, xpath: str):
    try:
        elements = driver.find_elements(By.XPATH, xpath)
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
            elements = driver.find_elements(By.XPATH, selector)
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
                    wait.until(EC.presence_of_element_located((By.XPATH, SEARCH_FIRST_PRODUCT_LINK_XPATH)))
                except Exception:
                    pass

                try:
                    first = driver.find_element(By.XPATH, SEARCH_FIRST_PRODUCT_LINK_XPATH)
                    href = first.get_attribute("href")
                    if href and PRODUCT_URL_PATTERN.search(href):
                        return href
                except Exception:
                    pass
            except Exception:
                pass

            stage = "open_home"
            driver.get(HOME_URL)
            wait.until(EC.presence_of_element_located((By.XPATH, "//body")))

            stage = "wait_preloader"
            try:
                wait.until(EC.invisibility_of_element_located((By.XPATH, "//*[@id='page-preloader']")))
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
                try:
                    candidate = driver.find_element(By.XPATH, HEADER_SEARCH_INPUT_XPATH_FALLBACK)
                    if candidate.is_displayed() and candidate.is_enabled():
                        header_input = candidate
                except Exception:
                    header_input = None

            if header_input is None:
                header_input = wait.until(EC.presence_of_element_located((By.XPATH, HEADER_SEARCH_INPUT_XPATH)))

            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", header_input)
            except Exception:
                pass

            if not _safe_click(driver=driver, element=header_input):
                raise ParserExecutionError("Unable to focus search input.")

            stage = "obtain_search_input"
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
                try:
                    btn = driver.find_element(By.XPATH, HEADER_SEARCH_SUBMIT_XPATH_FALLBACK)
                    submitted = _safe_click(driver=driver, element=btn)
                except Exception:
                    submitted = False
            if not submitted:
                try:
                    search_input.send_keys(Keys.ENTER)
                except Exception:
                    pass

            stage = "wait_search_page"
            try:
                wait.until(lambda d: "/search/" in ((getattr(d, "current_url", "") or "")))
            except Exception:
                try:
                    driver.get(urljoin(HOME_URL, f"/ukr/search/?Search={quote_plus(query)}"))
                except Exception:
                    pass

            stage = "resolve_first_product"
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, SEARCH_FIRST_PRODUCT_LINK_XPATH)))
            except Exception:
                pass
            try:
                first = driver.find_element(By.XPATH, SEARCH_FIRST_PRODUCT_LINK_XPATH)
                href = first.get_attribute("href")
                if href and PRODUCT_URL_PATTERN.search(href):
                    return href
            except Exception:
                pass

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

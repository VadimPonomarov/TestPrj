import os
import re
import shutil
from datetime import datetime
from typing import Optional

from core.exceptions import ParserExecutionError
from core.schemas import ProductData
from ..base.parser import BaseBrainParser

from ...services.parsers import BrainProductParser


class SeleniumBrainParser(BaseBrainParser):
    """Parser implementation using Selenium for JavaScript-heavy pages."""

    HOME_URL = "https://brain.com.ua/"
    PRODUCT_URL_PATTERN = re.compile(r"-p\d+\.html(?:$|\?)")
    HEADER_SEARCH_INPUT_XPATH = "/html/body/header/div[1]/div/div/div[2]/form/input[1]"
    HEADER_SEARCH_SUBMIT_XPATH = "/html/body/header/div[1]/div/div/div[2]/form/input[2]"
    
    def _parse(self, *, query: Optional[str] = None, url: Optional[str] = None) -> ProductData:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.common.exceptions import TimeoutException
            
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            chrome_options.add_argument("--lang=en-US")
            
            driver_path = os.getenv("CHROMEDRIVER_PATH") or shutil.which("chromedriver")
            if not driver_path:
                driver_path = "chromedriver"

            driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
            
            try:
                self._apply_headers(driver=driver)

                wait = WebDriverWait(driver, 20)
                resolved_url = self._resolve_product_url(
                    driver=driver,
                    wait=wait,
                    EC=EC,
                    By=By,
                    Keys=Keys,
                    query=query,
                    url=url,
                )

                driver.get(resolved_url)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

                html = driver.page_source
                parser = BrainProductParser(resolved_url, html=html)
                raw_payload = parser.parse()
                if not raw_payload:
                    raise ParserExecutionError("No data returned from Selenium parser.")

                product = ProductData.from_mapping(raw_payload)
                product.source_url = resolved_url
                return product
                
            except Exception as e:
                self.logger.error(f"Error during Selenium parsing: {str(e)}")
                raise ParserExecutionError(f"Failed to parse product: {str(e)}")
                
            finally:
                driver.quit()
                
        except ImportError:
            raise ParserExecutionError(
                "Selenium dependencies not found. Please install with: pip install selenium"
            )
        except Exception as e:
            raise ParserExecutionError(f"Unexpected error in Selenium parser: {str(e)}")

    def _apply_headers(self, *, driver) -> None:
        headers = {
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Referer": "https://www.google.com/",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",
        }
        user_agent = (
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:126.0) "
            "Gecko/20100101 Firefox/126.0"
        )

        try:
            driver.execute_cdp_cmd("Network.enable", {})
            driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {"headers": headers})
            driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": user_agent})
        except Exception:
            return

    def _dump_debug_html(self, *, driver, label: str) -> None:
        try:
            base_dir = os.path.join(os.getcwd(), "temp")
            os.makedirs(base_dir, exist_ok=True)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(base_dir, f"selenium_debug_{label}_{timestamp}.html")
            html = driver.page_source or ""
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(html)
            self.logger.error("Saved Selenium debug HTML to %s", path)
        except Exception:
            return

    def _dismiss_overlays(self, *, driver, By) -> None:
        selectors = [
            "button.cookie__agree",
            "button.cookie-agree",
            "button#cookie-accept",
            "button[aria-label='Accept cookies']",
            ".modal__close",
            ".popup-close",
            "[aria-label='Close']",
            ".fancybox-close",
        ]

        for selector in selectors:
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

    def _first_visible_by_css(self, *, driver, By, selector: str):
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

    def _safe_click(self, *, driver, element) -> bool:
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

    def _resolve_product_url(
        self,
        *,
        driver,
        wait,
        EC,
        By,
        Keys,
        query: Optional[str],
        url: Optional[str],
    ) -> str:
        if query:
            stage = "open_home"
            try:
                driver.get(self.HOME_URL)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

                stage = "wait_preloader"
                try:
                    wait.until(EC.invisibility_of_element_located((By.ID, "page-preloader")))
                except Exception:
                    pass

                stage = "dismiss_overlays"
                self._dismiss_overlays(driver=driver, By=By)

                stage = "focus_search_input"
                header_input = None
                try:
                    candidate = driver.find_element(By.XPATH, self.HEADER_SEARCH_INPUT_XPATH)
                    if candidate.is_displayed() and candidate.is_enabled():
                        header_input = candidate
                except Exception:
                    header_input = None

                if header_input is None:
                    header_input = self._first_visible_by_css(
                        driver=driver, By=By, selector=".quick-search-input"
                    )
                if header_input is None:
                    header_input = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".quick-search-input"))
                    )

                try:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", header_input
                    )
                except Exception:
                    pass

                if not self._safe_click(driver=driver, element=header_input):
                    raise ParserExecutionError("Unable to focus search input.")

                stage = "wait_qsr_block"
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".qsr-block")))
                except Exception:
                    pass

                stage = "obtain_search_input"
                search_input = self._first_visible_by_css(
                    driver=driver, By=By, selector=".qsr-input"
                )
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
                    btn = driver.find_element(By.XPATH, self.HEADER_SEARCH_SUBMIT_XPATH)
                    submitted = self._safe_click(driver=driver, element=btn)
                except Exception:
                    submitted = False
                if not submitted:
                    for selector in (
                        ".qsr-submit",
                        ".search-button-first-form",
                        "form input[type='submit']",
                    ):
                        btn = self._first_visible_by_css(driver=driver, By=By, selector=selector)
                        if btn and self._safe_click(driver=driver, element=btn):
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
                    show_all = self._first_visible_by_css(
                        driver=driver, By=By, selector=".qsr-showall"
                    )
                    if show_all is not None:
                        self._safe_click(driver=driver, element=show_all)
                except Exception:
                    pass

                stage = "open_first_product"
                for selector in (
                    ".qsr-products-list a[href*='-p'][href*='.html']",
                    ".qsr-products a[href*='-p'][href*='.html']",
                    "a[href*='-p'][href*='.html']",
                ):
                    first = self._first_visible_by_css(driver=driver, By=By, selector=selector)
                    if first is None:
                        continue
                    href = None
                    try:
                        href = first.get_attribute("href")
                    except Exception:
                        href = None
                    if self._safe_click(driver=driver, element=first):
                        try:
                            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
                        except Exception:
                            pass
                        current = getattr(driver, "current_url", "") or ""
                        if current and self.PRODUCT_URL_PATTERN.search(current):
                            return current
                    if href and self.PRODUCT_URL_PATTERN.search(href):
                        return href

                current = getattr(driver, "current_url", "") or ""
                if current and self.PRODUCT_URL_PATTERN.search(current):
                    return current

                raise ParserExecutionError("Unable to resolve product URL from search results.")
            except Exception as exc:
                self._dump_debug_html(driver=driver, label=f"resolve_{stage}")
                msg = getattr(exc, "msg", None) or str(exc) or repr(exc)
                raise ParserExecutionError(f"{stage}: {msg}") from exc

        if not url:
            raise ParserExecutionError("Either 'query' or 'url' must be provided.")
        return url

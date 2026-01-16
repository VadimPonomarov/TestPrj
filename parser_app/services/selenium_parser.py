from contextlib import contextmanager
from typing import Iterable, Optional, Sequence, Tuple
import os
import shutil

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.exceptions import ParserExecutionError
from core.schemas import ProductData

from .base import BaseBrainParser
from .brain_parser import BrainProductParser

Selector = Tuple[str, str]


class SeleniumBrainParser(BaseBrainParser):
    """Selenium-based implementation of the brain.com.ua scraper."""

    BASE_URL = "https://brain.com.ua/"
    SEARCH_INPUT_SELECTORS: Sequence[Selector] = (
        (By.CSS_SELECTOR, "input[name='search']"),
        (By.CSS_SELECTOR, "input[type='search']"),
        (By.CSS_SELECTOR, "input.header-search__input"),
    )
    SEARCH_BUTTON_SELECTORS: Sequence[Selector] = (
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.CSS_SELECTOR, "button.header-search__submit"),
        (By.CSS_SELECTOR, "button.search-form__submit"),
    )
    RESULT_LINK_SELECTORS: Sequence[Selector] = (
        (By.CSS_SELECTOR, "a.product-card__title"),
        (By.CSS_SELECTOR, "a.product-name"),
        (By.CSS_SELECTOR, "a.product-item__title"),
        (By.CSS_SELECTOR, "a.catalog-item__title"),
        (By.CSS_SELECTOR, "a[href*='/product/']"),
    )
    PRODUCT_READY_SELECTORS: Sequence[Selector] = (
        (By.CSS_SELECTOR, "script[type='application/ld+json']"),
        (By.CSS_SELECTOR, "div.product"),
    )

    def __init__(self, *, headless: bool = True, page_load_timeout: int = 30) -> None:
        super().__init__()
        self.headless = headless
        self.page_load_timeout = page_load_timeout

    def _parse(self, *, query: Optional[str], url: Optional[str]) -> ProductData:
        with self._driver() as driver:
            wait = WebDriverWait(driver, 15)

            if query:
                target_url = self._process_query(driver, wait, query)
            elif url:
                target_url = url
                driver.get(target_url)
            else:  # pragma: no cover - guarded by BaseBrainParser
                raise ParserExecutionError("Neither query nor URL provided for Selenium parser.")

            self._wait_for_product_page(wait)
            page_html = driver.page_source

        parser = BrainProductParser(target_url, html=page_html)
        payload = parser.parse()
        if not payload:
            raise ParserExecutionError("Failed to extract product data from Selenium session.")

        product = ProductData.from_mapping(payload)
        product.source_url = target_url
        return product

    @contextmanager
    def _driver(self) -> Iterable[webdriver.Chrome]:
        options = Options()
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        options.add_argument("--lang=uk-UA")

        proxy_server = os.getenv("SELENIUM_PROXY_SERVER") or os.getenv("PLAYWRIGHT_PROXY_SERVER")
        if proxy_server:
            options.add_argument(f"--proxy-server={proxy_server}")
        if self.headless:
            options.add_argument("--headless=new")

        driver_path = shutil.which("chromedriver")
        if not driver_path:
            raise ParserExecutionError("ChromeDriver executable not found on PATH.")

        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(self.page_load_timeout)
        try:
            yield driver
        finally:
            driver.quit()

    def _process_query(self, driver: webdriver.Chrome, wait: WebDriverWait, query: str) -> str:
        driver.get(self.BASE_URL)
        search_input = self._find_first(driver, self.SEARCH_INPUT_SELECTORS)
        search_input.clear()
        search_input.send_keys(query)

        submit_button = self._find_first(driver, self.SEARCH_BUTTON_SELECTORS)
        submit_button.click()

        self._wait_for_results(wait)
        first_link = self._find_first(driver, self.RESULT_LINK_SELECTORS)
        current_handle = driver.current_window_handle
        first_link.click()

        self._switch_to_new_tab(driver, current_handle)
        return driver.current_url

    def _find_first(self, driver: webdriver.Chrome, selectors: Sequence[Selector]):
        for by, value in selectors:
            elements = driver.find_elements(by, value)
            if elements:
                return elements[0]
        raise ParserExecutionError(f"Failed to locate element using selectors: {selectors}")

    def _switch_to_new_tab(self, driver: webdriver.Chrome, original_handle: str) -> None:
        WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) >= 1)
        for handle in driver.window_handles:
            if handle != original_handle:
                driver.switch_to.window(handle)
                return
        driver.switch_to.window(original_handle)

    def _wait_for_results(self, wait: WebDriverWait) -> None:
        try:
            wait.until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-card")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-item")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.catalog-items")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/product/']")),
                )
            )
        except TimeoutException as exc:
            raise ParserExecutionError("Search results did not load in time.") from exc

    def _wait_for_product_page(self, wait: WebDriverWait) -> None:
        try:
            wait.until(
                EC.any_of(*(EC.presence_of_element_located(selector) for selector in self.PRODUCT_READY_SELECTORS))
            )
        except TimeoutException as exc:
            raise ParserExecutionError("Product page did not load in time.") from exc


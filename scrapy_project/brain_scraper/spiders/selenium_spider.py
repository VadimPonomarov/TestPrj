import os
import shutil
from typing import Optional
from urllib.parse import quote_plus

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


def _resolve_chromedriver_path() -> str:
    path = os.getenv("CHROMEDRIVER_PATH") or shutil.which("chromedriver")
    if path:
        return path
    try:
        from webdriver_manager.chrome import ChromeDriverManager

        return ChromeDriverManager().install()
    except Exception:
        return "chromedriver"


def _create_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    options = Options()
    options.page_load_strategy = "eager"
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--mute-audio")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_experimental_option(
        "prefs",
        {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
            "profile.managed_default_content_settings.fonts": 2,
            "profile.managed_default_content_settings.media_stream": 2,
            "profile.managed_default_content_settings.sound": 2,
        },
    )

    return webdriver.Chrome(
        service=Service(_resolve_chromedriver_path()),
        options=options,
    )


def _pick_visible_pair(driver):
    pairs = [
        (HOME_SEARCH_INPUT_XPATH_FALLBACK, HOME_SEARCH_SUBMIT_XPATH_FALLBACK),
        (HOME_SEARCH_INPUT_XPATH, HOME_SEARCH_SUBMIT_XPATH),
    ]
    for input_xpath, submit_xpath in pairs:
        try:
            nodes = driver.find_elements("xpath", input_xpath)
            if not nodes:
                continue
            if nodes[0].is_displayed():
                return input_xpath, submit_xpath
        except Exception:
            continue
    return HOME_SEARCH_INPUT_XPATH, HOME_SEARCH_SUBMIT_XPATH


def _selenium_job(*, query: str) -> tuple[str, str]:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    driver = _create_driver()
    try:
        wait = WebDriverWait(driver, 30)
        driver.get(HOME_URL)

        input_xpath, submit_xpath = _pick_visible_pair(driver)
        wait.until(EC.presence_of_element_located((By.XPATH, input_xpath)))
        search_input = driver.find_element(By.XPATH, input_xpath)
        search_input.clear()
        search_input.send_keys(query)

        submit = driver.find_element(By.XPATH, submit_xpath)
        try:
            submit.click()
        except Exception:
            try:
                driver.execute_script("arguments[0].click();", submit)
            except Exception:
                try:
                    search_input.send_keys(Keys.ENTER)
                except Exception:
                    pass

        # If UI click did not navigate, fall back to direct search URL.
        search_url = f"https://brain.com.ua/ukr/search/?Search={quote_plus(query)}"
        try:
            wait.until(lambda d: "/search/" in ((getattr(d, "current_url", "") or "")))
        except Exception:
            driver.get(search_url)

        wait.until(EC.presence_of_element_located((By.XPATH, SEARCH_FIRST_PRODUCT_LINK_XPATH)))
        first_link = driver.find_element(By.XPATH, SEARCH_FIRST_PRODUCT_LINK_XPATH)
        try:
            first_link.click()
        except Exception:
            try:
                driver.execute_script("arguments[0].click();", first_link)
            except Exception:
                pass

        wait.until(EC.presence_of_element_located((By.XPATH, PRODUCT_CODE_XPATH)))

        try:
            btn = driver.find_elements(By.XPATH, ALL_CHARACTERISTICS_BUTTON_XPATH)
            if btn:
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn[0])
                    btn[0].click()
                except Exception:
                    try:
                        driver.execute_script("arguments[0].click();", btn[0])
                    except Exception:
                        pass
        except Exception:
            pass

        source_url = getattr(driver, "current_url", "") or HOME_URL
        html = getattr(driver, "page_source", None) or ""
        return source_url, html
    finally:
        try:
            driver.quit()
        except Exception:
            pass


class BrainSeleniumSpider(scrapy.Spider):
    name = "brain_selenium"

    custom_settings = {
        "DOWNLOAD_DELAY": float(os.getenv("SCRAPY_SELENIUM_DOWNLOAD_DELAY", "0.5")),
        "CONCURRENT_REQUESTS": int(os.getenv("SCRAPY_SELENIUM_CONCURRENT_REQUESTS", "1")),
        "CLOSESPIDER_TIMEOUT": int(os.getenv("SCRAPY_SELENIUM_CLOSESPIDER_TIMEOUT", "180")),
    }

    def __init__(self, query: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        defaults = ProductScrapeRequestSerializer.get_default_payload(ParserType.SELENIUM.value)
        self.query = query or defaults.get("query") or DEFAULT_QUERY

    def start_requests(self):
        yield scrapy.Request(HOME_URL, callback=self.parse, dont_filter=True)

    def parse(self, response: scrapy.http.Response):
        d = deferToThread(_selenium_job, query=self.query)

        def _on_success(result):
            source_url, html = result
            selector = Selector(text=html)
            item = extract_product_item(
                selector=selector,
                source_url=source_url,
                metadata={"parser": "ScrapySelenium", "query": self.query},
            )
            return [item]

        def _on_error(failure):
            self.logger.error("Selenium spider error: %s", failure)
            return []

        d.addCallback(_on_success)
        d.addErrback(_on_error)
        return d

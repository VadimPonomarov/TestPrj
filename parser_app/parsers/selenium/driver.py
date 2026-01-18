from __future__ import annotations

import os
import shutil

from ..config import BROWSER_EXTRA_HEADERS, BROWSER_USER_AGENT


def build_chrome_options():
    from selenium.webdriver.chrome.options import Options

    chrome_options = Options()
    chrome_binary = (
        os.getenv("CHROME_BINARY")
        or os.getenv("CHROME_BIN")
        or os.getenv("GOOGLE_CHROME_SHIM")
    )
    if chrome_binary:
        chrome_options.binary_location = chrome_binary

    chrome_options.page_load_strategy = "eager"
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_experimental_option(
        "prefs",
        {
            "profile.managed_default_content_settings.images": 2,
        },
    )
    chrome_options.add_argument("--lang=en-US")
    return chrome_options


def resolve_chromedriver_path() -> str:
    driver_path = os.getenv("CHROMEDRIVER_PATH") or shutil.which("chromedriver")
    if driver_path:
        return driver_path
    try:
        from webdriver_manager.chrome import ChromeDriverManager

        return ChromeDriverManager().install()
    except Exception:
        return "chromedriver"


def create_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service

    return webdriver.Chrome(
        service=Service(resolve_chromedriver_path()),
        options=build_chrome_options(),
    )


def apply_headers(*, driver) -> None:
    try:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {"headers": dict(BROWSER_EXTRA_HEADERS)})
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": BROWSER_USER_AGENT})
    except Exception:
        return

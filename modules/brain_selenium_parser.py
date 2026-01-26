import argparse
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from urllib.parse import quote_plus
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from parser_app.common.constants import *
from parser_app.common.csvio import *
from parser_app.common.db import *
from parser_app.common.decorators import time_execution
from parser_app.common.output import *
from parser_app.common.schema import Product
from parser_app.common.utils import coerce_decimal, extract_int

QUERY = DEFAULT_QUERY


def _is_product_url(url: str) -> bool:
    return "-p" in (url or "") and ".html" in (url or "")


def _text_or_empty(driver: webdriver.Chrome, xpath: str) -> str:
    try:
        el = driver.find_element(By.XPATH, xpath)
        text = (el.text or "").strip()
        if not text:
            text = (el.get_attribute("textContent") or "").strip()
        if not text:
            text = (el.get_attribute("innerText") or "").strip()
        return " ".join(text.split())
    except Exception:
        return ""


def _find_text_or_none(driver: webdriver.Chrome, xpath: str) -> Optional[str]:
    try:
        el = driver.find_element(By.XPATH, xpath)
        text = (el.text or "").strip()
        if not text:
            text = (el.get_attribute("textContent") or "").strip()
        if not text:
            text = (el.get_attribute("innerText") or "").strip()
        text = " ".join(text.split())
        return text or None
    except Exception:
        return None


def _extract_characteristics(driver: webdriver.Chrome) -> Dict[str, str]:
    data: Dict[str, str] = {}
    rows = driver.find_elements(
        By.XPATH,
        CHARACTERISTICS_ROWS_XPATH,
    )
    for row in rows:
        try:
            key = row.find_element(By.XPATH, "./span[1]").text
            value = row.find_element(By.XPATH, "./span[2]").text
            key = " ".join((key or "").split())
            value = " ".join((value or "").split())
            if key and value:
                data[key] = value
        except Exception:
            continue
    return data


def _open_all_characteristics(driver: webdriver.Chrome, wait: WebDriverWait) -> None:
    try:
        anchor = driver.find_element(By.XPATH, CHARACTERISTICS_ANCHOR_XPATH)
        driver.execute_script("arguments[0].scrollIntoView(true);", anchor)
    except Exception:
        try:
            wrapper = driver.find_element(By.XPATH, "//div[@id='br-characteristics']")
            driver.execute_script("arguments[0].scrollIntoView(true);", wrapper)
        except Exception:
            return

    try:
        button = driver.find_element(
            By.XPATH,
            ALL_CHARACTERISTICS_BUTTON_XPATH,
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", button)
        try:
            button.click()
        except Exception:
            driver.execute_script("arguments[0].click();", button)
    except Exception:
        return

    try:
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@id='br-pr-7']")))
    except Exception:
        return


def _extract_images(driver: webdriver.Chrome) -> List[str]:
    urls: List[str] = []
    nodes = driver.find_elements(
        By.XPATH, "//div[contains(@class,'main-pictures-block')]//img[@src]"
    )
    for n in nodes:
        src = (n.get_attribute("src") or "").strip()
        if src and not src.startswith("data:"):
            urls.append(src)
    return urls


def _extract_prices(driver: webdriver.Chrome) -> tuple[Optional[Decimal], Optional[Decimal]]:
    # Current price (text) - take the first price block.
    current_text = _find_text_or_none(
        driver,
        PRICE_XPATH,
    )

    # Old price (if sale) - appears inside div.old-price.
    old_text = _find_text_or_none(driver, OLD_PRICE_XPATH)

    current_price = coerce_decimal(current_text)
    old_price = coerce_decimal(old_text)

    if old_price is not None and current_price is not None:
        # old is regular, current is sale
        return old_price, current_price

    return current_price, None


def parse_selenium(url: str, query: str) -> Product:
    options = webdriver.ChromeOptions()
    # Headless mode
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Disable images and media
    prefs = {
        'profile.managed_default_content_settings.images': 2,  # Disable images
        'profile.managed_default_content_settings.stylesheets': 2,  # Disable CSS
        'profile.managed_default_content_settings.media_stream': 2,  # Disable media
        'profile.managed_default_content_settings.mixed_script': 2,  # Disable mixed scripts
        'profile.managed_default_content_settings.javascript': 1,  # Keep JS enabled for dynamic content
    }
    options.add_experimental_option('prefs', prefs)
    
    options.add_argument("--mute-audio")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("--window-size=1920,1080")
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

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )

    try:
        wait = WebDriverWait(driver, 30)

        start_url = (url or "").strip() or HOME_URL
        start_query = (query or "").strip() or DEFAULT_QUERY

        if _is_product_url(start_url):
            driver.get(start_url)
        else:
            driver.get(HOME_URL)

            input_xpath = HOME_SEARCH_INPUT_XPATH
            submit_xpath = HOME_SEARCH_SUBMIT_XPATH
            for ix, sx in (
                (HOME_SEARCH_INPUT_XPATH_FALLBACK, HOME_SEARCH_SUBMIT_XPATH_FALLBACK),
                (HOME_SEARCH_INPUT_XPATH, HOME_SEARCH_SUBMIT_XPATH),
            ):
                try:
                    nodes = driver.find_elements(By.XPATH, ix)
                    if nodes and nodes[0].is_displayed():
                        input_xpath = ix
                        submit_xpath = sx
                        break
                except Exception:
                    continue

            wait.until(EC.presence_of_element_located((By.XPATH, input_xpath)))
            search_input = driver.find_element(By.XPATH, input_xpath)
            try:
                search_input.click()
            except Exception:
                pass
            try:
                search_input.send_keys(Keys.CONTROL, "a")
                search_input.send_keys(Keys.DELETE)
            except Exception:
                try:
                    driver.execute_script("arguments[0].value = ''", search_input)
                except Exception:
                    pass

            try:
                search_input.send_keys(start_query)
            except Exception:
                driver.execute_script(
                    "arguments[0].value = arguments[1]", search_input, start_query
                )

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

            # Ensure we land on the full search results page.
            search_url = f"https://brain.com.ua/ukr/search/?Search={quote_plus(start_query)}"
            try:
                wait.until(
                    lambda d: "/search/" in ((getattr(d, "current_url", "") or ""))
                )
            except Exception:
                driver.get(search_url)

            # Wait until product links are available in the DOM.
            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//a[contains(@href,'-p') and contains(@href,'.html')]")
                )
            )

            wait.until(
                EC.presence_of_element_located((By.XPATH, SEARCH_FIRST_PRODUCT_LINK_XPATH))
            )
            first_link = driver.find_element(By.XPATH, SEARCH_FIRST_PRODUCT_LINK_XPATH)
            href = None
            try:
                href = first_link.get_attribute("href")
            except Exception:
                href = None
            if href:
                driver.get(urljoin(driver.current_url, href))
            else:
                try:
                    first_link.click()
                except Exception:
                    try:
                        driver.execute_script("arguments[0].click();", first_link)
                    except Exception:
                        pass

        wait.until(EC.presence_of_element_located((By.XPATH, "//h1")))
        # Ensure product code is present (page fully loaded)
        wait.until(
            EC.presence_of_element_located(
                (By.XPATH, PRODUCT_CODE_XPATH)
            )
        )

        _open_all_characteristics(driver, wait)

        source_url = driver.current_url

        name = _text_or_empty(driver, "//h1[1]")
        product_code = _text_or_empty(driver, PRODUCT_CODE_XPATH)
        manufacturer = ""
        try:
            manufacturer = (driver.find_element(By.XPATH, "//*[@data-vendor][1]").get_attribute("data-vendor") or "").strip()
        except Exception:
            manufacturer = ""

        review_count = 0
        review_anchor_text = _find_text_or_none(driver, REVIEW_ANCHOR_XPATH)
        if review_anchor_text:
            review_count = extract_int(review_anchor_text)

        color = _text_or_empty(driver, COLOR_VALUE_XPATH)
        storage = _text_or_empty(driver, STORAGE_VALUE_XPATH)
        screen_diagonal = _text_or_empty(driver, SCREEN_DIAGONAL_XPATH)
        display_resolution = _text_or_empty(driver, DISPLAY_RESOLUTION_XPATH)

        characteristics = _extract_characteristics(driver)
        price, sale_price = _extract_prices(driver)
        images = _extract_images(driver)

        return Product(
            name=name,
            color=color,
            storage=storage,
            manufacturer=manufacturer,
            price=price,
            sale_price=sale_price,
            images=images,
            product_code=product_code,
            review_count=review_count,
            screen_diagonal=screen_diagonal,
            display_resolution=display_resolution,
            characteristics=characteristics,
            source_url=source_url,
            metadata={"parser": "Selenium"},
        )
    finally:
        try:
            driver.quit()
        except Exception:
            pass


@time_execution("Parsing - Selenium")
def main() -> None:
    parser = argparse.ArgumentParser(description="Parse product page using Selenium")
    parser.add_argument(
        "url",
        type=str,
        nargs="?",
        default=HOME_URL,
        help="Product URL (direct) or start URL for search workflow (default: home page)",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=DEFAULT_QUERY,
        help="Search query (used when url is not a product page)",
    )
    parser.add_argument("--csv", type=str, default="", help="Path to output CSV file")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--save-db", action="store_true", dest="save_db", help="Save to database")
    group.add_argument("--no-save-db", action="store_false", dest="save_db", help="Do not save to database")
    parser.set_defaults(save_db=False)
    args = parser.parse_args()

    product = parse_selenium(args.url, args.query)
    print_mapping(product.to_dict())

    csv_path = args.csv
    if not csv_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = f"temp/assignment/outputs/selenium_{ts}.csv"

    save_csv_row(product.to_dict(), csv_path)
    print(f"[INFO] CSV saved: {csv_path}")

    if args.save_db:
        save_product_via_serializer(data=product.to_dict())
        print(f"[INFO] Product persisted to DB via serializer (product_code={product.product_code})")


if __name__ == "__main__":
    main()

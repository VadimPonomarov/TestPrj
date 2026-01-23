import argparse
import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus
from urllib.parse import urljoin

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from parser_app.common.constants import *
from parser_app.common.csvio import *
from parser_app.common.db import *
from parser_app.common.output import *
from parser_app.common.schema import *
from parser_app.common.utils import *


QUERY = DEFAULT_QUERY


def _text_or_empty(page, xpath: str) -> str:
    try:
        el = page.locator(f"xpath={xpath}").first
        text = ""
        try:
            text = el.inner_text(timeout=5000) or ""
        except Exception:
            text = ""

        if not text.strip():
            try:
                text = el.text_content(timeout=5000) or ""
            except Exception:
                text = ""

        return " ".join(text.split())
    except Exception:
        return ""


def _resolve_visible_pair(page) -> tuple[str, str]:
    pairs = [
        (HOME_SEARCH_INPUT_XPATH_FALLBACK, HOME_SEARCH_SUBMIT_XPATH_FALLBACK),
        (HOME_SEARCH_INPUT_XPATH, HOME_SEARCH_SUBMIT_XPATH),
    ]
    for input_xpath, submit_xpath in pairs:
        try:
            loc = page.locator(f"xpath={input_xpath}").first
            if loc.count() < 1:
                continue
            if loc.is_visible():
                return input_xpath, submit_xpath
        except Exception:
            continue
    return HOME_SEARCH_INPUT_XPATH, HOME_SEARCH_SUBMIT_XPATH


def _goto_first_product_from_search(page) -> None:
    page.wait_for_selector(
        f"xpath={SEARCH_FIRST_PRODUCT_LINK_XPATH}", timeout=20000, state="attached"
    )
    link = page.locator(f"xpath={SEARCH_FIRST_PRODUCT_LINK_XPATH}").first
    href = link.get_attribute("href")
    if not href:
        raise RuntimeError("Failed to resolve first product link href")
    page.goto(urljoin(page.url, href), wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=30000)
    except Exception:
        pass


def _attr_or_empty(page, xpath: str, attr: str) -> str:
    try:
        el = page.locator(f"xpath={xpath}").first
        val = el.get_attribute(attr, timeout=5000)
        return (val or "").strip()
    except Exception:
        return ""


def _extract_characteristics(page) -> Dict[str, str]:
    data: Dict[str, str] = {}
    rows = page.locator(
        f"xpath={CHARACTERISTICS_ROWS_XPATH}"
    )
    count = rows.count()
    for idx in range(count):
        row = rows.nth(idx)
        try:
            key = row.locator("xpath=./span[1]").inner_text(timeout=5000)
            value = row.locator("xpath=./span[2]").inner_text(timeout=5000)
            key = " ".join((key or "").split())
            value = " ".join((value or "").split())
            if key and value:
                data[key] = value
        except Exception:
            continue
    return data


def _open_all_characteristics(page) -> None:
    try:
        anchor = page.locator(f"xpath={CHARACTERISTICS_ANCHOR_XPATH}").first
        anchor.scroll_into_view_if_needed(timeout=5000)
    except Exception:
        try:
            wrapper = page.locator("xpath=//div[@id='br-characteristics']").first
            wrapper.scroll_into_view_if_needed(timeout=5000)
        except Exception:
            return

    try:
        button = page.locator(
            f"xpath={ALL_CHARACTERISTICS_BUTTON_XPATH}"
        ).first
        button.scroll_into_view_if_needed(timeout=5000)
        try:
            button.click(timeout=5000)
        except Exception:
            page.evaluate("el => el && el.click()", button)
    except Exception:
        return

    try:
        page.wait_for_selector("xpath=//div[@id='br-pr-7']", timeout=15000)
    except Exception:
        return


def _extract_images(page) -> List[str]:
    urls: List[str] = []
    imgs = page.locator("xpath=//div[contains(@class,'main-pictures-block')]//img[@src]")
    count = imgs.count()
    for idx in range(count):
        src = (imgs.nth(idx).get_attribute("src") or "").strip()
        if src and not src.startswith("data:"):
            urls.append(src)
    return urls


def _extract_prices(page) -> tuple[Optional[Decimal], Optional[Decimal]]:
    current_text = _text_or_empty(
        page,
        PRICE_XPATH,
    )
    old_text = _text_or_empty(page, OLD_PRICE_XPATH)

    current_price = coerce_decimal(current_text)
    old_price = coerce_decimal(old_text)

    if old_price is not None and current_price is not None:
        return old_price, current_price

    return current_price, None


def parse() -> Product:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        def _route_handler(route):
            try:
                resource_type = route.request.resource_type
            except Exception:
                resource_type = None

            if resource_type in {"image", "media", "font", "stylesheet"}:
                try:
                    route.abort()
                except Exception:
                    route.continue_()
                return

            route.continue_()

        page.route("**/*", _route_handler)

        try:
            page.goto(HOME_URL, wait_until="domcontentloaded", timeout=60000)

            input_xpath, submit_xpath = _resolve_visible_pair(page)
            page.wait_for_selector(f"xpath={input_xpath}", timeout=20000)
            page.locator(f"xpath={input_xpath}").fill(QUERY, timeout=20000)

            try:
                page.keyboard.press("Enter")
            except Exception:
                pass

            try:
                page.locator(f"xpath={submit_xpath}").first.click(timeout=2000, force=True)
            except Exception:
                pass

            search_url = f"https://brain.com.ua/ukr/search/?Search={quote_plus(QUERY)}"
            try:
                page.wait_for_url("**/search/**", timeout=15000)
            except Exception:
                page.goto(search_url, wait_until="domcontentloaded", timeout=60000)

            _goto_first_product_from_search(page)

            page.wait_for_selector("xpath=//h1", timeout=20000, state="attached")

            page.wait_for_selector(
                f"xpath={PRODUCT_CODE_XPATH}",
                timeout=20000,
                state="attached",
            )

            _open_all_characteristics(page)

            source_url = page.url

            name = _text_or_empty(page, "//h1[1]")
            product_code = _text_or_empty(
                page, PRODUCT_CODE_XPATH
            )
            manufacturer = _attr_or_empty(page, "//*[@data-vendor][1]", "data-vendor")

            review_anchor_text = _text_or_empty(page, REVIEW_ANCHOR_XPATH)
            review_count = extract_int(review_anchor_text) if review_anchor_text else 0

            color = _text_or_empty(page, COLOR_VALUE_XPATH)
            storage = _text_or_empty(page, STORAGE_VALUE_XPATH)
            screen_diagonal = _text_or_empty(page, SCREEN_DIAGONAL_XPATH)
            display_resolution = _text_or_empty(page, DISPLAY_RESOLUTION_XPATH)

            characteristics = _extract_characteristics(page)
            price, sale_price = _extract_prices(page)
            images = _extract_images(page)

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
                metadata={"parser": "Playwright"},
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="")
    parser.add_argument("--save-db", action="store_true")
    args = parser.parse_args()

    product = parse()
    print_mapping(product.to_dict())

    csv_path = args.csv
    if not csv_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = f"temp/assignment/outputs/playwright_{ts}.csv"

    save_csv_row(product.to_dict(), csv_path)

    if args.save_db:
        defaults = {
            "name": product.name,
            "source_url": product.source_url,
            "price": product.price,
            "sale_price": product.sale_price,
            "manufacturer": product.manufacturer or None,
            "color": product.color or None,
            "storage": product.storage or None,
            "review_count": product.review_count,
            "screen_diagonal": product.screen_diagonal or None,
            "display_resolution": product.display_resolution or None,
            "images": product.images,
            "characteristics": product.characteristics,
            "metadata": product.metadata,
        }
        save_product_to_db(product_code=product.product_code, defaults=defaults)


if __name__ == "__main__":
    main()

import argparse
import asyncio
import json
import logging
import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

from playwright.async_api import async_playwright, Page

from parser_app.common.constants import (
    ALL_CHARACTERISTICS_BUTTON_XPATH,
    CHARACTERISTICS_ANCHOR_XPATH,
    CHARACTERISTICS_ROWS_XPATH,
    DEFAULT_QUERY,
    HOME_URL,
    HOME_SEARCH_INPUT_XPATH,
    HOME_SEARCH_INPUT_XPATH_FALLBACK,
    HOME_SEARCH_SUBMIT_XPATH,
    HOME_SEARCH_SUBMIT_XPATH_FALLBACK,
    OLD_PRICE_XPATH,
    PRICE_XPATH,
    PRODUCT_CODE_XPATH,
    SEARCH_FIRST_PRODUCT_LINK_XPATH,
)
from parser_app.common.csvio import save_csv_row
from parser_app.common.db import save_product_via_serializer
from parser_app.common.decorators import time_execution
from parser_app.common.output import print_mapping
from parser_app.common.schema import Product
from parser_app.common.utils import coerce_decimal

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

QUERY = DEFAULT_QUERY


def _is_product_url(url: str) -> bool:
    return "-p" in (url or "") and ".html" in (url or "")


def _empty_product(source_url: str = "", metadata: Optional[Dict[str, Any]] = None) -> Product:
    return Product(
        name="",
        color="",
        storage="",
        manufacturer="",
        price=None,
        sale_price=None,
        source_url=source_url,
        metadata=metadata or {},
    )


async def _text_or_empty_async(page: Page, xpath: str) -> str:
    """Get text content from element matching xpath or return empty string."""
    try:
        el = page.locator(f"xpath={xpath}").first
        if not await el.is_visible(timeout=5000):
            return ""

        try:
            text = await el.inner_text(timeout=5000) or ""
            if text.strip():
                return " ".join(text.split())
        except Exception as e:
            logger.debug(f"Error getting inner_text: {e}")

        try:
            text = await el.text_content(timeout=5000) or ""
            return " ".join(text.split())
        except Exception as e:
            logger.debug(f"Error getting text_content: {e}")
            return ""
    except Exception as e:
        logger.debug(f"Error in _text_or_empty_async: {e}")
        return ""


async def _resolve_visible_pair_async(page: Page) -> Tuple[str, str]:
    """Resolve the correct input/submit button pair that's visible on the page."""
    pairs = [
        (HOME_SEARCH_INPUT_XPATH_FALLBACK, HOME_SEARCH_SUBMIT_XPATH_FALLBACK),
        (HOME_SEARCH_INPUT_XPATH, HOME_SEARCH_SUBMIT_XPATH),
    ]

    for input_xpath, submit_xpath in pairs:
        try:
            input_visible = await page.locator(f"xpath={input_xpath}").is_visible()
            submit_visible = await page.locator(f"xpath={submit_xpath}").is_visible()

            if input_visible and submit_visible:
                return input_xpath, submit_xpath
        except Exception as e:
            logger.debug(f"Error checking visibility for pair {input_xpath}: {e}")
            continue

    logger.warning("No visible input/submit pair found, using defaults")
    return HOME_SEARCH_INPUT_XPATH, HOME_SEARCH_SUBMIT_XPATH


async def _goto_first_product_from_search_async(page: Page) -> None:
    """Navigate to the first product from search results."""
    try:
        await page.wait_for_selector(
            f"xpath={SEARCH_FIRST_PRODUCT_LINK_XPATH}", timeout=15000, state="attached"
        )

        link = page.locator(f"xpath={SEARCH_FIRST_PRODUCT_LINK_XPATH}").first
        href = await link.get_attribute("href")

        if not href:
            raise RuntimeError("Failed to resolve first product link href")

        logger.info(f"Navigating to product: {href}")
        await page.goto(urljoin(page.url, href), wait_until="domcontentloaded", timeout=45000)
        try:
            await page.wait_for_selector("xpath=//h1", timeout=12000)
        except Exception:
            pass

        try:
            await page.wait_for_selector(f"xpath={PRODUCT_CODE_XPATH}", timeout=12000)
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Error navigating to product: {e}")
        raise


async def _attr_or_empty_async(page: Page, xpath: str, attr: str) -> str:
    """Get attribute value from element or return empty string."""
    try:
        el = page.locator(f"xpath={xpath}").first
        if await el.is_visible(timeout=5000):
            val = await el.get_attribute(attr, timeout=5000)
            return (val or "").strip()
        return ""
    except Exception as e:
        logger.debug(f"Error getting attribute '{attr}': {e}")
        return ""


async def _extract_characteristics_async(page: Page) -> Dict[str, str]:
    """Extract product characteristics asynchronously."""
    data: Dict[str, str] = {}
    rows = page.locator(f"xpath={CHARACTERISTICS_ROWS_XPATH}")
    count = await rows.count()

    for idx in range(count):
        row = rows.nth(idx)
        try:
            key_element = row.locator("xpath=./span[1]")
            value_element = row.locator("xpath=./span[2]")

            key = await key_element.inner_text(timeout=5000)
            value = await value_element.inner_text(timeout=5000)

            key = " ".join((key or "").split())
            value = " ".join((value or "").split())

            if key and value:
                data[key] = value
        except Exception as e:
            logger.debug(f"Error extracting characteristic at index {idx}: {e}")
            continue

    return data


async def _open_all_characteristics_async(page: Page) -> None:
    """Ensure that all characteristics are expanded before extraction."""
    try:
        anchor = page.locator(f"xpath={CHARACTERISTICS_ANCHOR_XPATH}").first
        await anchor.scroll_into_view_if_needed(timeout=5000)
    except Exception:
        try:
            wrapper = page.locator("xpath=//div[@id='br-characteristics']").first
            await wrapper.scroll_into_view_if_needed(timeout=5000)
        except Exception as e:
            logger.debug(f"Unable to scroll to characteristics section: {e}")
            return

    try:
        button = page.locator(f"xpath={ALL_CHARACTERISTICS_BUTTON_XPATH}").first
        await button.scroll_into_view_if_needed(timeout=5000)
        try:
            await button.click(timeout=5000)
        except Exception:
            await page.evaluate("el => el && el.click()", button)
    except Exception as e:
        logger.debug(f"Unable to trigger 'all characteristics' button: {e}")
        return

    try:
        await page.wait_for_selector("xpath=//div[@id='br-pr-7']", timeout=15000)
    except Exception as e:
        logger.debug(f"Characteristics expansion confirmation timed out: {e}")


async def _extract_images_async(page: Page) -> List[str]:
    """Collect all image URLs for the product."""
    urls: List[str] = []
    imgs = page.locator("xpath=//div[contains(@class,'main-pictures-block')]//img[@src]")
    count = await imgs.count()

    for idx in range(count):
        img = imgs.nth(idx)
        try:
            src = (await img.get_attribute("src") or "").strip()
            if src and not src.startswith("data:"):
                urls.append(src)
        except Exception as e:
            logger.debug(f"Error extracting image at index {idx}: {e}")
            continue

    return urls


async def _extract_prices_async(page: Page) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    """Extract current and old prices from the page."""
    current_text = await _text_or_empty_async(page, PRICE_XPATH)
    old_text = await _text_or_empty_async(page, OLD_PRICE_XPATH)

    current_price = coerce_decimal(current_text)
    old_price = coerce_decimal(old_text)

    if old_price is not None and current_price is not None:
        return old_price, current_price

    return current_price, None


async def _extract_name_async(page: Page) -> str:
    """Extract product name from JSON-LD or fallback to DOM."""
    try:
        json_ld_script = await page.evaluate(
            """() => {
            const script = document.querySelector('script[type="application/ld+json"]');
            return script ? script.textContent : null;
        }"""
        )

        if json_ld_script:
            try:
                json_ld = json.loads(json_ld_script)
                if isinstance(json_ld, dict) and "name" in json_ld:
                    return str(json_ld["name"])
                if isinstance(json_ld, list):
                    for item in json_ld:
                        if isinstance(item, dict) and "name" in item:
                            return str(item["name"])
            except json.JSONDecodeError as e:
                logger.debug(f"JSON-LD parsing error: {e}")

        name_element = await page.query_selector("h1")
        if name_element:
            name = await name_element.text_content()
            return name.strip() if name else ""

        return ""
    except Exception as e:
        logger.debug(f"Error extracting name: {e}")
        return ""


async def _extract_review_count_async(page: Page) -> int:
    """Extract review count from the page."""
    try:
        review_text = await page.evaluate(
            """() => {
            const reviewLink = Array.from(document.querySelectorAll('a[href*="#reviews"]'))[0];
            return reviewLink ? reviewLink.textContent.trim() : '';
        }"""
        )

        if not review_text:
            return 0

        match = re.search(r"(\d+)", review_text)
        return int(match.group(1)) if match else 0
    except Exception as e:
        logger.debug(f"Error extracting review count: {e}")
        return 0


async def parse_async(url: str, query: str, fast: bool = False) -> Product:
    """Parse product page asynchronously."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
            ],
        )

        context = None
        try:
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                java_script_enabled=True,
                bypass_csp=True,
                ignore_https_errors=True,
                offline=False,
                has_touch=False,
                is_mobile=False,
                color_scheme="light",
                reduced_motion="reduce",
                accept_downloads=False,
                service_workers="block",
                permissions=[],
                timezone_id="Europe/Kiev",
                locale="en-US",
            )

            page = await context.new_page()
            page.set_default_timeout(12000)

            async def _route_handler(route):
                try:
                    resource_type = route.request.resource_type
                    if resource_type in {"image", "media", "font", "stylesheet"}:
                        await route.abort()
                    else:
                        await route.continue_()
                except Exception:
                    try:
                        await route.abort()
                    except Exception:
                        pass

            await context.route("**/*", _route_handler)

            try:
                response = await page.goto(url, timeout=45000, wait_until="domcontentloaded")
                if not response or not response.ok:
                    logger.error(f"Failed to load URL {url}")
                    return _empty_product(source_url=url, metadata={"parser": "Playwright"})
            except Exception as e:
                logger.error(f"Navigation error for {url}: {e}")
                return _empty_product(source_url=url, metadata={"parser": "Playwright"})

            is_product_url = _is_product_url(page.url or "")
            if not is_product_url:
                try:
                    if (page.url or "").rstrip("/") == HOME_URL.rstrip("/"):
                        input_xpath, submit_xpath = await _resolve_visible_pair_async(page)
                        await page.fill(f"xpath={input_xpath}", query)

                        try:
                            await page.evaluate(
                                """() => {
                                const el = document.querySelector('#page-preloader');
                                if (el) el.style.pointerEvents = 'none';
                            }"""
                            )
                        except Exception:
                            pass

                        try:
                            preloader = page.locator("#page-preloader")
                            if await preloader.count() > 0:
                                await preloader.first.wait_for(state="hidden", timeout=2000)
                        except Exception:
                            pass

                        try:
                            await page.press(f"xpath={input_xpath}", "Enter")
                        except Exception:
                            try:
                                await page.locator(f"xpath={submit_xpath}").scroll_into_view_if_needed(
                                    timeout=5000
                                )
                                await page.click(f"xpath={submit_xpath}", timeout=5000, force=True)
                            except Exception:
                                await page.evaluate(
                                    "(xp) => { const el = document.evaluate(xp, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue; if (el) el.click(); }",
                                    submit_xpath,
                                )

                        try:
                            await page.wait_for_load_state("domcontentloaded", timeout=8000)
                        except Exception:
                            pass

                        try:
                            await page.wait_for_selector(
                                f"xpath={SEARCH_FIRST_PRODUCT_LINK_XPATH}",
                                timeout=15000,
                                state="attached",
                            )
                        except Exception:
                            pass

                        await _goto_first_product_from_search_async(page)
                    else:
                        logger.warning(f"Non-product page URL provided: {page.url}")
                except Exception as e:
                    logger.error(f"Failed to navigate from non-product page to product: {e}")
                    return _empty_product(source_url=page.url or url, metadata={"parser": "Playwright"})

            selectors = [
                "h1[itemprop='name']",
                ".product-title",
                "h1.product-name",
                "h1",
            ]

            for selector in selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    break
                except Exception:
                    continue

            try:
                await page.wait_for_selector(f"xpath={PRICE_XPATH}", timeout=8000)
            except Exception:
                pass

            if not fast:
                await _open_all_characteristics_async(page)

            name = await _extract_name_async(page)
            price, sale_price = await _extract_prices_async(page)
            images = [] if fast else await _extract_images_async(page)
            characteristics = await _extract_characteristics_async(page)
            review_count = await _extract_review_count_async(page)

            product_code = await _text_or_empty_async(page, PRODUCT_CODE_XPATH)
            manufacturer = await _attr_or_empty_async(page, "//*[@data-vendor][1]", "data-vendor")

            color = characteristics.get("Колір", "")
            storage = characteristics.get("Вбудована пам'ять", "") or characteristics.get(
                "Вбудована пам’ять", ""
            )
            screen_diagonal = characteristics.get("Діагональ екрана", "")
            display_resolution = characteristics.get("Роздільна здатність екрана", "")

            return Product(
                name=name,
                color=color,
                storage=storage,
                manufacturer=manufacturer or "",
                price=price,
                sale_price=sale_price,
                images=images,
                product_code=product_code or "",
                review_count=review_count or 0,
                screen_diagonal=screen_diagonal,
                display_resolution=display_resolution,
                characteristics=characteristics,
                source_url=page.url,
                metadata={"parser": "Playwright"},
            )
        except Exception as e:
            logger.error(f"Error parsing {url}: {e}")
            return _empty_product(source_url=url, metadata={"parser": "Playwright"})
        finally:
            if context:
                try:
                    await context.close()
                except Exception as err:
                    logger.debug(f"Error closing context: {err}")
            try:
                await browser.close()
            except Exception as err:
                logger.debug(f"Error closing browser: {err}")


async def async_main() -> None:
    """Async entry point for the parser."""
    parser = argparse.ArgumentParser(description="Parse product page using Playwright")
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
    parser.add_argument(
        "--csv", type=str, default="", help="Path to output CSV file (optional)"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Faster run (skips expensive steps like expanding all characteristics)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--save-db", action="store_true", dest="save_db", help="Save to database")
    group.add_argument(
        "--no-save-db",
        action="store_false",
        dest="save_db",
        help="Do not save to database",
    )
    parser.set_defaults(save_db=False)

    args = parser.parse_args()

    try:
        logger.info(f"Starting parser for URL: {args.url}")
        query = (args.query or "").strip() or DEFAULT_QUERY
        url = (args.url or "").strip() or HOME_URL
        product = await parse_async(url, query, fast=bool(args.fast))

        print_mapping(product.to_dict())

        csv_path = args.csv
        if not csv_path:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = f"temp/assignment/outputs/playwright_{ts}.csv"

        save_csv_row(product.to_dict(), csv_path)
        logger.info(f"CSV saved: {csv_path}")

        if args.save_db:
            if (product.name or "").strip() and (product.product_code or "").strip():
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: save_product_via_serializer(data=product.to_dict())
                )
                logger.info(
                    "Product persisted to DB via serializer "
                    f"(product_code={product.product_code})"
                )
            else:
                logger.warning(
                    "Skip DB save: required fields are blank "
                    f"(name={product.name!r}, product_code={product.product_code!r})"
                )

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


@time_execution("Parsing - Playwright")
def main() -> None:
    """Synchronous entry point that runs the async main function."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("Parser stopped by user")
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}")
        raise


if __name__ == "__main__":
    main()

import argparse
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

from asgiref.sync import async_to_sync
from lxml import html
from playwright.async_api import async_playwright, Page

from parser_app.common.constants import (
    ALL_CHARACTERISTICS_BUTTON_XPATH,
    CHARACTERISTICS_ANCHOR_XPATH,
    CHARACTERISTICS_ROWS_XPATH,
    DEFAULT_QUERY,
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

QUERY = DEFAULT_QUERY


async def _text_or_empty_async(page: Page, xpath: str) -> str:
    try:
        el = page.locator(f"xpath={xpath}").first
        text = ""
        try:
            text = await el.inner_text(timeout=5000) or ""
        except Exception:
            text = ""

        if not text.strip():
            try:
                text = await el.text_content(timeout=5000) or ""
            except Exception:
                text = ""

        return " ".join(text.split())
    except Exception:
        return ""


async def _resolve_visible_pair_async(page: Page) -> Tuple[str, str]:
    pairs = [
        (HOME_SEARCH_INPUT_XPATH_FALLBACK, HOME_SEARCH_SUBMIT_XPATH_FALLBACK),
        (HOME_SEARCH_INPUT_XPATH, HOME_SEARCH_SUBMIT_XPATH),
    ]
    for input_xpath, submit_xpath in pairs:
        try:
            if await page.locator(f"xpath={input_xpath}").is_visible() and await page.locator(
                f"xpath={submit_xpath}"
            ).is_visible():
                return input_xpath, submit_xpath
        except Exception:
            continue
    return HOME_SEARCH_INPUT_XPATH, HOME_SEARCH_SUBMIT_XPATH


async def _goto_first_product_from_search_async(page: Page) -> None:
    await page.wait_for_selector(
        f"xpath={SEARCH_FIRST_PRODUCT_LINK_XPATH}", timeout=20000, state="attached"
    )
    link = page.locator(f"xpath={SEARCH_FIRST_PRODUCT_LINK_XPATH}").first
    href = await link.get_attribute("href")
    if not href:
        raise RuntimeError("Failed to resolve first product link href")
    await page.goto(urljoin(page.url, href), wait_until="domcontentloaded", timeout=60000)
    try:
        await page.wait_for_load_state("networkidle", timeout=30000)
    except Exception as e:
        print(f"Warning: {e}")


async def _attr_or_empty_async(page: Page, xpath: str, attr: str) -> str:
    try:
        el = page.locator(f"xpath={xpath}").first
        if await el.is_visible():
            val = await el.get_attribute(attr, timeout=5000)
            return (val or "").strip()
        return ""
    except Exception as e:
        print(f"[WARNING] Error getting attribute '{attr}': {e}")
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
            continue
    return data


async def _open_all_characteristics_async(page: Page) -> None:
    try:
        anchor = page.locator(f"xpath={CHARACTERISTICS_ANCHOR_XPATH}").first
        await anchor.scroll_into_view_if_needed(timeout=5000)
    except Exception:
        try:
            wrapper = page.locator("xpath=//div[@id='br-characteristics']").first
            await wrapper.scroll_into_view_if_needed(timeout=5000)
        except Exception:
            return

    try:
        button = page.locator(
            f"xpath={ALL_CHARACTERISTICS_BUTTON_XPATH}"
        ).first
        await button.scroll_into_view_if_needed(timeout=5000)
        try:
            button.click(timeout=5000)
        except Exception:
            await page.evaluate("el => el && el.click()", button)
    except Exception:
        return

    try:
        await page.wait_for_selector("xpath=//div[@id='br-pr-7']", timeout=15000)
    except Exception:
        return


async def _extract_images_async(page: Page) -> List[str]:
    urls: List[str] = []
    imgs = page.locator("xpath=//div[contains(@class,'main-pictures-block')]//img[@src]")
    count = await imgs.count()
    for idx in range(count):
        img = imgs.nth(idx)
        src = (await img.get_attribute("src") or "").strip()
        if src and not src.startswith("data:"):
            urls.append(src)
    return urls


async def _extract_prices_async(page: Page) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    current_text = await _text_or_empty_async(page, PRICE_XPATH)
    old_text = await _text_or_empty_async(page, OLD_PRICE_XPATH)

    current_price = coerce_decimal(current_text)
    old_price = coerce_decimal(old_text)

    if old_price is not None and current_price is not None:
        return old_price, current_price

    return current_price, None


async def parse_async(url: str) -> Product:
    """Async version of parse function using async/await"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-gpu',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            java_script_enabled=True,
            bypass_csp=True,
            ignore_https_errors=True,
            offline=False,
            has_touch=False,
            is_mobile=False,
            color_scheme='light',
            reduced_motion='reduce',
            accept_downloads=False,
            service_workers='block',
            permissions=[],
            timezone_id='Europe/Kiev',
            locale='en-US'
        )
        
        # Block resources
        await context.route('**/*.{png,jpg,jpeg,webp,svg,gif,ico}', lambda route: route.abort())
        await context.route('**/*.css', lambda route: route.abort())
        await context.route('**/*.woff*', lambda route: route.abort())
        await context.route('**/*.ttf', lambda route: route.abort())
        await context.route('**/*.mp4', lambda route: route.abort())
        await context.route('**/*.webm', lambda route: route.abort())
        await context.route('**/*.mp3', lambda route: route.abort())

        try:
            # Create new page and set up request interception
            page = await context.new_page()
            
            # Set up request handler
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

            # Navigate to the page with a reliable waiting strategy
            try:
                response = await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                if not response or not response.ok:
                    return Product()  # Return empty product on failure
            except Exception:
                return Product()  # Return empty product on error

            # Wait for the product title with multiple possible selectors
            selectors = [
                "h1[itemprop='name']",
                ".product-title",
                "h1.product-name",
                "h1"
            ]
            
            for selector in selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    break
                except Exception:
                    continue
            
            # Add a small delay to ensure dynamic content is loaded
            await page.wait_for_timeout(3000)

            # Get page content
            content = await page.content()
            tree = html.fromstring(content)
            
            page_title = await page.title()

            # Extract product details
            name = await _extract_name_async(page)
            price, sale_price = await _extract_prices_async(page)
            images = await _extract_images_async(page)
            characteristics = await _extract_characteristics_async(page)
            review_count = await _extract_review_count_async(page)

            # Open all characteristics if needed
            await _open_all_characteristics_async(page)

            source_url = page.url

            name = await _text_or_empty_async(page, "//h1[1]")
            product_code = await _text_or_empty_async(
                page, PRODUCT_CODE_XPATH
            )
            manufacturer = await _attr_or_empty_async(page, "//*[@data-vendor][1]", "data-vendor")

            # Extract color and storage from characteristics if available
            color = characteristics.get("Колір", "")
            storage = characteristics.get("Вбудована пам'ять", "") or characteristics.get("Вбудована пам’ять", "")
            
            # Extract screen diagonal and resolution
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
                source_url=url,
                metadata={"parser": "Playwright"},
            )

        finally:
            # Clean up resources
            try:
                await context.close()
            except Exception:
                pass
            try:
                await browser.close()
            except Exception:
                pass


async def _extract_name_async(page) -> str:
    """Extract product name from the page.
    
    Args:
        page: Playwright page object
        
    Returns:
        str: Extracted product name or empty string if not found
    """
    try:
        # First try to get name from JSON-LD data
        json_ld_script = await page.evaluate('''() => {
            const script = document.querySelector('script[type="application/ld+json"]');
            return script ? script.textContent : null;
        }''')
        
        if json_ld_script:
            try:
                json_ld = json.loads(json_ld_script)
                if isinstance(json_ld, dict) and 'name' in json_ld:
                    return str(json_ld['name'])
                elif isinstance(json_ld, list):
                    for item in json_ld:
                        if isinstance(item, dict) and 'name' in item:
                            return str(item['name'])
            except json.JSONDecodeError:
                pass
        
        # Fallback to XPath if JSON-LD not found or invalid
        name_element = await page.query_selector('h1')
        if name_element:
            name = await name_element.text_content()
            return name.strip() if name else ""
            
        return ""
    except Exception as e:
        print(f"Error extracting name: {e}")
        return ""

# Update helper functions to be async
async def _extract_review_count_async(page) -> int:
    """Extract review count from the page.
    
    Args:
        page: Playwright page object
        
    Returns:
        int: Number of reviews or 0 if not found
    """
    try:
        # Look for review link and extract the number
        review_text = await page.evaluate('''() => {
            const reviewLink = Array.from(document.querySelectorAll('a[href*="#reviews"]'))[0];
            return reviewLink ? reviewLink.textContent.trim() : '';
        }''')
        
        if not review_text:
            return 0
            
        # Extract first number from the text
        import re
        match = re.search(r'(\d+)', review_text)
        return int(match.group(1)) if match else 0
    except Exception:
        return 0


async def _open_all_characteristics_async(page):
    """Async version of _open_all_characteristics"""
    buttons = await page.query_selector_all("button.more-charact")
    for btn in buttons:
        try:
            await btn.click()
            await page.wait_for_timeout(300)  # Small delay between clicks
        except Exception:
            continue


def parse(url: str = None) -> Product:
    """Synchronous wrapper for the async parse_async function.
    
    Args:
        url: URL of the product page to parse. If not provided, uses the default QUERY.
    """
    url_to_parse = url or QUERY
    return async_to_sync(parse_async)(url_to_parse)


@time_execution("Parsing - Playwright")
def main() -> None:
    parser = argparse.ArgumentParser(description="Parse product page using Playwright")
    parser.add_argument("url", type=str, nargs='?', default="https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_15_128GB_Black-p1044347.html",
                        help="URL of the product page (default: iPhone 15 example)")
    parser.add_argument("--csv", type=str, default="", help="Path to output CSV file")
    parser.add_argument("--no-save-db", action="store_false", dest="save_db", help="Disable saving to database")
    args = parser.parse_args()

    product = parse(args.url)
    print_mapping(product.to_dict())

    csv_path = args.csv
    if not csv_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = f"temp/assignment/outputs/playwright_{ts}.csv"

    save_csv_row(product.to_dict(), csv_path)
    print(f"[INFO] CSV saved: {csv_path}")

    if args.save_db:
        save_product_via_serializer(data=product.to_dict())
        print(f"[INFO] Product persisted to DB via serializer (product_code={product.product_code})")


if __name__ == "__main__":
    main()

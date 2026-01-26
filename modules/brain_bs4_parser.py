import argparse
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests
from lxml import html

from parser_app.common.constants import *
from parser_app.common.csvio import *
from parser_app.common.db import *
from parser_app.common.output import *
from parser_app.common.schema import Product
from parser_app.common.utils import coerce_decimal
from parser_app.common.decorators import time_execution

def _extract_jsonld_product(tree: html.HtmlElement) -> Optional[Dict[str, Any]]:
    for node in tree.xpath("//script[@type='application/ld+json']/text()"):  # type: ignore[call-arg]
        raw = (node or "").strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue

        candidates: List[Dict[str, Any]] = []
        if isinstance(payload, dict) and isinstance(payload.get("@graph"), list):
            candidates = [n for n in payload.get("@graph", []) if isinstance(n, dict)]
        elif isinstance(payload, list):
            candidates = [n for n in payload if isinstance(n, dict)]
        elif isinstance(payload, dict):
            candidates = [payload]

        for item in candidates:
            item_type = item.get("@type")
            if item_type == "Product" or (
                isinstance(item_type, list) and "Product" in item_type
            ):
                return item

    return None


def _extract_brand_name(product_json: Optional[Dict[str, Any]]) -> str:
    if not product_json:
        return ""
    brand = product_json.get("brand")
    if isinstance(brand, dict):
        return str(brand.get("name") or "")
    if isinstance(brand, str):
        return brand
    return ""


def _extract_images(product_json: Optional[Dict[str, Any]]) -> List[str]:
    if not product_json:
        return []
    images = product_json.get("image") or []
    if isinstance(images, str):
        images = [images]
    if isinstance(images, list):
        result = []
        for img in images:
            if isinstance(img, str) and img:
                result.append(img)
        return result
    return []


def _normalise_offers(product_json: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    offers = product_json.get("offers") if product_json else {}
    if isinstance(offers, list) and offers:
        offers = offers[0]
    if not isinstance(offers, dict):
        offers = {}

    price = offers.get("price") if offers else None
    sale_price = None

    if product_json:
        declared_price = product_json.get("price")
        if declared_price and declared_price != price:
            sale_price = price
            price = declared_price

    return {
        "price": price,
        "sale_price": sale_price,
        "availability": offers.get("availability") if offers else None,
        "price_currency": offers.get("priceCurrency") if offers else None,
    }


def _extract_review_count(tree: html.HtmlElement) -> int:
    nodes = tree.xpath("//a[contains(@href,'#reviews')][1]")
    if not nodes:
        return 0
    text = " ".join((nodes[0].text_content() or "").split())
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else 0


def _extract_product_code(tree: html.HtmlElement) -> str:
    nodes = tree.xpath(
        "//div[@id='product_code']//span[contains(@class,'br-pr-code-val')]/text()"
    )
    if nodes:
        return str(nodes[0]).strip()
    return ""


def _extract_characteristics(tree: html.HtmlElement) -> Dict[str, str]:
    result: Dict[str, str] = {}
    rows = tree.xpath(
        "//div[@id='br-pr-7']//div[contains(@class,'br-pr-chr')]//div[count(span)>=2]"
    )
    for row in rows:
        key_nodes = row.xpath("./span[1]")
        val_nodes = row.xpath("./span[2]")
        if not key_nodes or not val_nodes:
            continue
        key = " ".join((key_nodes[0].text_content() or "").split())
        value = " ".join((val_nodes[0].text_content() or "").split())
        if key and value:
            result[key] = value
    return result


def _extract_display_info(characteristics: Dict[str, str]) -> tuple[str, str]:
    diagonal = ""
    resolution = ""

    if "Діагональ екрану" in characteristics:
        diagonal = characteristics["Діагональ екрану"].replace('"', "").strip()

    if "Роздільна здатність екрану" in characteristics:
        resolution = characteristics["Роздільна здатність екрану"].strip()

    return diagonal, resolution


@time_execution("Парсинг с использованием BeautifulSoup")
def parse_product(url: str) -> Product:
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()

    tree = html.fromstring(response.text)

    product_json = _extract_jsonld_product(tree)
    offers = _normalise_offers(product_json)
    images = _extract_images(product_json)

    name_nodes = tree.xpath("//h1[1]")
    name = " ".join((name_nodes[0].text_content() or "").split()) if name_nodes else ""

    characteristics = _extract_characteristics(tree)
    screen_diagonal, display_resolution = _extract_display_info(characteristics)

    color_nodes = tree.xpath(
        "//span[normalize-space()='Колір']/following-sibling::span[1]//a[1]/text()"
    )
    color = str(color_nodes[0]).strip() if color_nodes else ""

    storage_nodes = tree.xpath(
        '//span[normalize-space()="Вбудована пам\'ять" or normalize-space()="Вбудована пам\u2019ять"]/following-sibling::span[1]//a[1]/text()'
    )
    storage = str(storage_nodes[0]).strip() if storage_nodes else ""

    product_code = _extract_product_code(tree)

    price = coerce_decimal(offers.get("price"))
    sale_price = coerce_decimal(offers.get("sale_price"))

    return Product(
        name=name,
        color=color,
        storage=storage,
        manufacturer=_extract_brand_name(product_json),
        price=price,
        sale_price=sale_price,
        images=images,
        product_code=product_code,
        review_count=_extract_review_count(tree),
        screen_diagonal=screen_diagonal,
        display_resolution=display_resolution,
        characteristics=characteristics,
        source_url=url,
        metadata={"parser": "BS4"},
    )

@time_execution("Parsing - BS4")
def main() -> None:
    parser = argparse.ArgumentParser(description="Parse product page using BS4")
    parser.add_argument("url", type=str, nargs='?', default="https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_15_128GB_Black-p1044347.html", 
                        help="URL of the product page (default: iPhone 15 example)")
    parser.add_argument("--csv", type=str, default="", help="Path to output CSV file")
    parser.add_argument("--no-save-db", action="store_false", dest="save_db", help="Disable saving to database")
    args = parser.parse_args()

    product = parse_product(args.url)
    print_mapping(product.to_dict())

    csv_path = args.csv
    if not csv_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = f"temp/assignment/outputs/bs4_{ts}.csv"

    save_csv_row(product.to_dict(), csv_path)
    print(f"[INFO] CSV saved: {csv_path}")

    if args.save_db:
        save_product_via_serializer(data=product.to_dict())
        print(f"[INFO] Product persisted to DB via serializer (product_code={product.product_code})")


if __name__ == "__main__":
    main()

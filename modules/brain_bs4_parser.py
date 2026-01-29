import argparse
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from parser_app.common.constants import *
from parser_app.common.csvio import *
from parser_app.common.db import *
from parser_app.common.decorators import time_execution
from parser_app.common.output import *
from parser_app.common.schema import Product
from parser_app.common.utils import coerce_decimal


def _extract_jsonld_product(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    for node in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = (node.get_text() or "").strip()
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


def _extract_review_count(soup: BeautifulSoup) -> int:
    node = soup.select_one("a[href*='#reviews']")
    if not node:
        return 0
    text = " ".join((node.get_text(" ", strip=True) or "").split())
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else 0


def _extract_product_code(soup: BeautifulSoup) -> str:
    node = soup.select_one("#product_code span.br-pr-code-val")
    if node:
        return node.get_text(strip=True)
    return ""


def _extract_characteristics(soup: BeautifulSoup) -> Dict[str, str]:
    result: Dict[str, str] = {}
    rows = soup.select("#br-pr-7 .br-pr-chr div")
    for row in rows:
        spans = row.find_all("span")
        if len(spans) < 2:
            continue
        key = " ".join((spans[0].get_text(" ", strip=True) or "").split())
        value = " ".join((spans[1].get_text(" ", strip=True) or "").split())
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

    soup = BeautifulSoup(response.text, "lxml")

    product_json = _extract_jsonld_product(soup)
    offers = _normalise_offers(product_json)
    images = _extract_images(product_json)

    name_node = soup.find("h1")
    name = " ".join((name_node.get_text(" ", strip=True) or "").split()) if name_node else ""

    characteristics = _extract_characteristics(soup)
    screen_diagonal, display_resolution = _extract_display_info(characteristics)

    color = ""
    for label in soup.find_all("span"):
        if (label.get_text(strip=True) or "").strip() == "Колір":
            sib = label.find_next_sibling("span")
            if sib:
                a = sib.find("a")
                if a:
                    color = (a.get_text(strip=True) or "").strip()
            break

    storage = ""
    storage_labels = {"Вбудована пам'ять", "Вбудована пам’ять"}
    for label in soup.find_all("span"):
        if (label.get_text(strip=True) or "").strip() in storage_labels:
            sib = label.find_next_sibling("span")
            if sib:
                a = sib.find("a")
                if a:
                    storage = (a.get_text(strip=True) or "").strip()
            break

    product_code = _extract_product_code(soup)

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
        review_count=_extract_review_count(soup),
        screen_diagonal=screen_diagonal,
        display_resolution=display_resolution,
        characteristics=characteristics,
        source_url=url,
        metadata={"parser": "BS4"},
    )

@time_execution("Parsing - BS4")
def main() -> None:
    parser = argparse.ArgumentParser(description="Parse product page using BS4")
    parser.add_argument(
        "url",
        type=str,
        nargs="?",
        default="",
        help="URL of the product page",
    )
    parser.add_argument(
        "--url",
        type=str,
        default="",
        dest="url_opt",
        help="URL of the product page",
    )
    parser.add_argument("--csv", type=str, default="", help="Path to output CSV file")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--save-db", action="store_true", dest="save_db", help="Save to database")
    group.add_argument("--no-save-db", action="store_false", dest="save_db", help="Do not save to database")
    parser.set_defaults(save_db=False)
    args = parser.parse_args()

    url = (args.url_opt or args.url or "").strip() or "https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_15_128GB_Black-p1044347.html"
    product = parse_product(url)
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

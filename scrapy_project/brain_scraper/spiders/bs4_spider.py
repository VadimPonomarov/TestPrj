import os
import json
import re
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urljoin

import scrapy
from bs4 import BeautifulSoup

from core.enums import ParserType
from parser_app.serializers import ProductScrapeRequestSerializer

def _extract_jsonld_product(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    for node in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = (node.get_text() or "").strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue

        candidates: list[Dict[str, Any]] = []
        if isinstance(payload, dict) and isinstance(payload.get("@graph"), list):
            candidates = [n for n in payload.get("@graph", []) if isinstance(n, dict)]
        elif isinstance(payload, list):
            candidates = [n for n in payload if isinstance(n, dict)]
        elif isinstance(payload, dict):
            candidates = [payload]

        for item in candidates:
            item_type = item.get("@type")
            if item_type == "Product" or (isinstance(item_type, list) and "Product" in item_type):
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


def _extract_images(product_json: Optional[Dict[str, Any]]) -> list[str]:
    if not product_json:
        return []
    images = product_json.get("image") or []
    if isinstance(images, str):
        images = [images]
    if isinstance(images, list):
        result: list[str] = []
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


def _extract_review_count(product_json: Optional[Dict[str, Any]], soup: BeautifulSoup) -> int:
    if product_json:
        aggregate = product_json.get("aggregateRating")
        if isinstance(aggregate, dict):
            try:
                rc = int(aggregate.get("reviewCount") or 0)
            except (TypeError, ValueError):
                rc = 0
            if rc:
                return rc

    node = soup.select_one("a[href*='#reviews']")
    if not node:
        return 0
    text = " ".join((node.get_text(" ", strip=True) or "").split())
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else 0


def _extract_product_code(soup: BeautifulSoup) -> str:
    node = soup.select_one("#product_code span.br-pr-code-val")
    return node.get_text(strip=True) if node else ""


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


def _extract_labeled_value(soup: BeautifulSoup, label_texts: set[str]) -> str:
    for label in soup.find_all("span"):
        if (label.get_text(strip=True) or "").strip() in label_texts:
            sib = label.find_next_sibling("span")
            if not sib:
                return ""
            a = sib.find("a")
            if not a:
                return ""
            return (a.get_text(strip=True) or "").strip()
    return ""


def _normalise_image_url(base_url: str, src: str) -> str:
    raw = (src or "").strip()
    if not raw:
        return ""
    if raw.startswith("data:"):
        return ""
    if raw.startswith("//"):
        return "https:" + raw
    return urljoin(base_url, raw)


def _split_urls(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    return [u.strip() for u in raw.split(",") if u.strip()]


class BrainBs4Spider(scrapy.Spider):
    name = "brain_bs4"

    custom_settings = {
        "DOWNLOAD_DELAY": float(os.getenv("SCRAPY_BS4_DOWNLOAD_DELAY", "0.5")),
        "CONCURRENT_REQUESTS": int(os.getenv("SCRAPY_BS4_CONCURRENT_REQUESTS", "4")),
    }

    def __init__(self, urls: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        defaults = ProductScrapeRequestSerializer.get_default_payload(ParserType.BS4.value)
        resolved = _split_urls(urls) or ([defaults["url"]] if defaults.get("url") else [])
        if not resolved:
            raise ValueError("At least one URL is required for brain_bs4 spider")
        self.start_urls = list(resolved)

    def start_requests(self) -> Iterable[scrapy.Request]:
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse, dont_filter=True)

    def parse(self, response: scrapy.http.Response):
        html = getattr(response, "text", "") or ""
        soup = BeautifulSoup(html, "lxml")

        product_json = _extract_jsonld_product(soup)
        offers = _normalise_offers(product_json)

        name_node = soup.find("h1")
        name = " ".join((name_node.get_text(" ", strip=True) or "").split()) if name_node else ""

        characteristics = _extract_characteristics(soup)
        screen_diagonal, display_resolution = _extract_display_info(characteristics)

        color = _extract_labeled_value(soup, {"Колір"})
        storage = _extract_labeled_value(soup, {"Вбудована пам'ять", "Вбудована пам’ять"})

        product_code = _extract_product_code(soup)
        if not product_code and product_json:
            product_code = str(
                product_json.get("mpn")
                or product_json.get("sku")
                or product_json.get("gtin")
                or ""
            ).strip()
        review_count = _extract_review_count(product_json, soup)

        images_raw = _extract_images(product_json)
        images: list[str] = []
        for src in images_raw:
            resolved = _normalise_image_url(response.url, src)
            if resolved and resolved not in images:
                images.append(resolved)

        price = offers.get("price")
        sale_price = offers.get("sale_price")

        item = {
            "name": name or (str(product_json.get("name") or "").strip() if product_json else ""),
            "product_code": product_code,
            "source_url": response.url,
            "price": str(price) if price not in (None, "") else None,
            "sale_price": str(sale_price) if sale_price not in (None, "") else None,
            "manufacturer": _extract_brand_name(product_json),
            "color": color,
            "storage": storage,
            "review_count": review_count,
            "screen_diagonal": screen_diagonal,
            "display_resolution": display_resolution,
            "images": images,
            "characteristics": characteristics,
            "metadata": {"parser": "ScrapyBS4"},
        }

        yield item

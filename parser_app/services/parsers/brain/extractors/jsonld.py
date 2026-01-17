import json
import re
from typing import Any, Dict, Iterable, Optional

from bs4 import BeautifulSoup


def extract_product_json_ld(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    for script in scripts:
        try:
            payload = json.loads(script.string or "{}")
        except json.JSONDecodeError:
            continue

        candidates: Iterable[Dict[str, Any]]
        if isinstance(payload, dict) and "@graph" in payload:
            candidates = [
                node
                for node in payload.get("@graph", [])
                if isinstance(node, dict)
            ]
        elif isinstance(payload, list):
            candidates = [node for node in payload if isinstance(node, dict)]
        else:
            candidates = [payload] if isinstance(payload, dict) else []

        for node in candidates:
            node_type = node.get("@type")
            if node_type == "Product":
                return node
            if isinstance(node_type, list) and "Product" in node_type:
                return node

    return None


def normalise_offers(product_json: Optional[Dict[str, Any]]) -> Dict[str, Any]:
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


def extract_brand_name(product_json: Optional[Dict[str, Any]]) -> Optional[str]:
    brand = product_json.get("brand") if product_json else None
    if isinstance(brand, dict):
        return brand.get("name")
    if isinstance(brand, str):
        return brand
    return None


def extract_review_count(product_json: Optional[Dict[str, Any]], soup: Optional[BeautifulSoup]) -> int:
    if not product_json:
        return 0

    review_count = 0
    aggregate = product_json.get("aggregateRating")
    if isinstance(aggregate, dict):
        review_count = int(aggregate.get("reviewCount") or 0)

    if review_count:
        return review_count

    if soup:
        reviews_anchor = soup.find("a", href=re.compile("#reviews"))
        if reviews_anchor:
            match = re.search(r"(\d+)", reviews_anchor.get_text(" ", strip=True))
            if match:
                return int(match.group(1))

    return 0


def build_metadata(product_json: Optional[Dict[str, Any]], offers: Dict[str, Any]) -> Dict[str, Any]:
    if not product_json:
        return {}

    metadata: Dict[str, Any] = {
        "sku": product_json.get("sku"),
        "gtin": product_json.get("gtin") or product_json.get("gtin13"),
        "aggregate_rating": product_json.get("aggregateRating"),
        "offers": offers,
        "description": product_json.get("description"),
    }

    return {key: value for key, value in metadata.items() if value not in (None, "")}

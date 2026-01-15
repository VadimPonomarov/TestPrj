import json
import re
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup


class BrainProductParser:
    """Parser for extracting product information from brain.com.ua product pages."""

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, url: str, *, html: Optional[str] = None, timeout: int = 15) -> None:
        self.url = url
        self.timeout = timeout
        self._html = html
        self._soup: Optional[BeautifulSoup] = None
        self._product_json: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def parse(self) -> Dict[str, Any]:
        """Return structured product data extracted from the target page."""
        html = self._html or self._download_html()
        if not html:
            return {}

        self._soup = BeautifulSoup(html, "html.parser")
        self._product_json = self._extract_product_json_ld()

        if not self._product_json:
            return {}

        characteristics = self._extract_characteristics()
        screen_diagonal, display_resolution = self._extract_display_info(characteristics)

        images = self._product_json.get("image") or []
        if isinstance(images, str):
            images = [images]

        offers = self._normalise_offers()
        metadata = self._build_metadata(offers)

        color, storage = self._guess_color_and_storage(characteristics)

        data: Dict[str, Any] = {
            "name": self._product_json.get("name"),
            "product_code": self._product_json.get("mpn") or metadata.get("sku"),
            "source_url": self.url,
            "price": self._to_decimal(offers.get("price")),
            "sale_price": self._to_decimal(offers.get("sale_price")),
            "manufacturer": self._extract_brand_name(),
            "color": color,
            "storage": storage,
            "review_count": self._extract_review_count(),
            "screen_diagonal": screen_diagonal,
            "display_resolution": display_resolution,
            "images": images,
            "characteristics": characteristics,
            "metadata": metadata,
        }

        return {k: v for k, v in data.items() if v not in (None, "")}

    # ------------------------------------------------------------------
    # Network / HTML helpers
    # ------------------------------------------------------------------
    def _download_html(self) -> Optional[str]:
        try:
            response = requests.get(
                self.url,
                headers={"User-Agent": self.USER_AGENT},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.text
        except requests.RequestException:
            return None

    # ------------------------------------------------------------------
    # JSON-LD helpers
    # ------------------------------------------------------------------
    def _extract_product_json_ld(self) -> Optional[Dict[str, Any]]:
        if not self._soup:
            return None

        scripts = self._soup.find_all("script", attrs={"type": "application/ld+json"})
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

    # ------------------------------------------------------------------
    # Data extraction helpers
    # ------------------------------------------------------------------
    def _normalise_offers(self) -> Dict[str, Any]:
        offers = self._product_json.get("offers") if self._product_json else {}
        if isinstance(offers, list) and offers:
            offers = offers[0]
        if not isinstance(offers, dict):
            offers = {}

        price = offers.get("price")
        sale_price = None

        # Some pages duplicate regular price in the JSON-LD root
        if self._product_json:
            declared_price = self._product_json.get("price")
            if declared_price and declared_price != price:
                sale_price = price
                price = declared_price

        return {
            "price": price,
            "sale_price": sale_price,
            "availability": offers.get("availability"),
            "price_currency": offers.get("priceCurrency"),
        }

    def _extract_brand_name(self) -> Optional[str]:
        brand = self._product_json.get("brand") if self._product_json else None
        if isinstance(brand, dict):
            return brand.get("name")
        if isinstance(brand, str):
            return brand
        return None

    def _extract_review_count(self) -> int:
        if not self._product_json:
            return 0

        review_count = 0
        aggregate = self._product_json.get("aggregateRating")
        if isinstance(aggregate, dict):
            review_count = int(aggregate.get("reviewCount") or 0)

        if review_count:
            return review_count

        # Fallback to DOM lookup
        if self._soup:
            reviews_anchor = self._soup.find("a", href=re.compile("#reviews"))
            if reviews_anchor:
                match = re.search(r"(\d+)", reviews_anchor.get_text(" ", strip=True))
                if match:
                    return int(match.group(1))

        return 0

    def _build_metadata(self, offers: Dict[str, Any]) -> Dict[str, Any]:
        if not self._product_json:
            return {}

        metadata: Dict[str, Any] = {
            "sku": self._product_json.get("sku"),
            "gtin": self._product_json.get("gtin") or self._product_json.get("gtin13"),
            "aggregate_rating": self._product_json.get("aggregateRating"),
            "offers": offers,
            "description": self._product_json.get("description"),
        }

        # Clean up None values
        return {key: value for key, value in metadata.items() if value not in (None, "")}

    def _extract_characteristics(self) -> Dict[str, Any]:
        if not self._soup:
            return {}

        characteristic_extractors = [
            self._extract_characteristics_from_dom,
            self._extract_characteristics_from_scripts,
        ]

        for extractor in characteristic_extractors:
            result = extractor()
            if result:
                return result

        return {}

    def _extract_characteristics_from_dom(self) -> Dict[str, Any]:
        if not self._soup:
            return {}

        characteristics: Dict[str, Any] = {}
        selectors: List[Tuple[str, str, str]] = [
            (
                "div.product-characteristic__item",
                "div.product-characteristic__title",
                "div.product-characteristic__value",
            ),
            (
                "div.product-properties__item",
                "div.product-properties__title",
                "div.product-properties__value",
            ),
            (
                "li.characteristics__list-item",
                "span.characteristics__name",
                "span.characteristics__value",
            ),
        ]

        for container_selector, key_selector, value_selector in selectors:
            containers = self._soup.select(container_selector)
            if not containers:
                continue

            for container in containers:
                key_node = container.select_one(key_selector)
                value_node = container.select_one(value_selector)
                key = key_node.get_text(" ", strip=True) if key_node else None
                value = value_node.get_text(" ", strip=True) if value_node else None
                if key and value:
                    characteristics[key] = value

            if characteristics:
                return characteristics

        # Try table based layout
        table = self._soup.select_one("table.characteristics, table.product-characteristics")
        if table:
            for row in table.select("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    key = cells[0].get_text(" ", strip=True)
                    value = cells[1].get_text(" ", strip=True)
                    if key and value:
                        characteristics[key] = value

        return characteristics

    def _extract_characteristics_from_scripts(self) -> Dict[str, Any]:
        if not self._soup:
            return {}

        script_nodes = self._soup.find_all("script")
        for script in script_nodes:
            script_text = script.string or script.get_text(strip=True)
            if not script_text or "character" not in script_text.lower():
                continue

            json_payload = self._extract_json_from_script(script_text)
            if not json_payload:
                continue

            if isinstance(json_payload, dict):
                possible = self._search_for_characteristics(json_payload)
                if possible:
                    return possible

            if isinstance(json_payload, list):
                for item in json_payload:
                    if isinstance(item, dict):
                        possible = self._search_for_characteristics(item)
                        if possible:
                            return possible

        return {}

    def _extract_json_from_script(self, script_text: str) -> Optional[Any]:
        # Remove assignments such as "window.__STATE__ = ..."
        match = re.search(r"=\s*(\{.*\})\s*;?$", script_text, re.DOTALL)
        if not match:
            match = re.search(r"(\{.*\})", script_text, re.DOTALL)
        if not match:
            return None

        candidate = match.group(1)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return None

    def _search_for_characteristics(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        candidates: List[Any] = [payload]
        seen: set[int] = set()

        while candidates:
            node = candidates.pop()
            if isinstance(node, dict):
                node_id = id(node)
                if node_id in seen:
                    continue
                seen.add(node_id)

                keys_lower = {str(k).lower() for k in node.keys()}
                if any("character" in key for key in keys_lower):
                    for key, value in node.items():
                        if isinstance(value, list) and all(isinstance(elem, dict) for elem in value):
                            mapped = self._list_of_dicts_to_mapping(value)
                            if mapped:
                                return mapped

                candidates.extend(node.values())
            elif isinstance(node, list):
                candidates.extend(node)

        return {}

    def _list_of_dicts_to_mapping(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        mapping: Dict[str, Any] = {}
        for item in items:
            key = item.get("name") or item.get("title") or item.get("label")
            value = item.get("value") or item.get("text")
            if key and value:
                mapping[str(key)] = value
        return mapping

    def _extract_display_info(self, characteristics: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        diagonal = None
        resolution = None

        diagonal_keys = [
            "Діагональ екрана",
            "Діагональ",
            "Діагональ екрану",
            "Диагональ экрана",
        ]
        resolution_keys = [
            "Роздільна здатність екрана",
            "Роздільна здатність",
            "Разрешение экрана",
            "Разрешение",
        ]

        for key in diagonal_keys:
            if key in characteristics:
                match = re.search(r"(\d+[\.,]?\d*)", characteristics[key])
                if match:
                    diagonal = match.group(1).replace(",", ".")
                    break

        for key in resolution_keys:
            if key in characteristics:
                match = re.search(r"(\d+\s*[xх×]\s*\d+)", characteristics[key], re.IGNORECASE)
                if match:
                    resolution = re.sub(r"\s+", "", match.group(1)).lower().replace("х", "x").replace("×", "x")
                    break

        return diagonal, resolution

    def _guess_color_and_storage(self, characteristics: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        color = characteristics.get("Колір") or characteristics.get("Цвет")
        storage = (
            characteristics.get("Вбудована пам'ять")
            or characteristics.get("Объем встроенной памяти")
            or characteristics.get("Пам'ять")
        )

        if not color and self._product_json and self._product_json.get("name"):
            color_match = re.search(
                r"(?i)\b(Black|Blue|White|Silver|Gold|Green|Red|Pink|Purple|Natural Titanium|Blue Titanium|Black Titanium)\b",
                self._product_json["name"],
            )
            if color_match:
                color = color_match.group(1)

        if not storage and self._product_json and self._product_json.get("name"):
            storage_match = re.search(r"(\d+\s?(?:GB|TB))", self._product_json["name"], re.IGNORECASE)
            if storage_match:
                storage = storage_match.group(1).upper().replace(" ", "")

        return color, storage

    def _to_decimal(self, value: Any) -> Optional[Decimal]:
        if value is None or value == "":
            return None
        try:
            return Decimal(str(value))
        except (ValueError, ArithmeticError):
            return None


def format_product_output(data: Dict[str, Any]) -> str:
    if not data:
        return "No product data extracted."

    lines = ["=" * 60, "BRAIN PRODUCT DATA", "=" * 60]
    simple_fields = [
        "name",
        "product_code",
        "manufacturer",
        "color",
        "storage",
        "price",
        "sale_price",
        "review_count",
        "screen_diagonal",
        "display_resolution",
    ]

    for field in simple_fields:
        value = data.get(field)
        if value is not None:
            lines.append(f"{field.replace('_', ' ').title()}: {value}")

    if data.get("images"):
        lines.append("Images:")
        for idx, url in enumerate(data["images"], start=1):
            lines.append(f"  {idx}. {url}")

    if data.get("characteristics"):
        lines.append("Characteristics:")
        for key, value in data["characteristics"].items():
            lines.append(f"  {key}: {value}")

    if data.get("metadata"):
        lines.append("Metadata:")
        for key, value in data["metadata"].items():
            lines.append(f"  {key}: {value}")

    lines.append("=" * 60)
    return "\n".join(lines)

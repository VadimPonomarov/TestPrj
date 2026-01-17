import re
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from bs4 import BeautifulSoup

from .extractors.characteristics import extract_characteristics, extract_display_info
from .extractors.jsonld import (
    build_metadata,
    extract_brand_name,
    extract_product_json_ld,
    extract_review_count,
    normalise_offers,
)
from .html import download_html


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

    def parse(self) -> Dict[str, Any]:
        """Return structured product data extracted from the target page."""
        html = self._html or download_html(self.url, user_agent=self.USER_AGENT, timeout=self.timeout)
        if not html:
            return {}

        soup = BeautifulSoup(html, "html.parser")
        product_json = extract_product_json_ld(soup)
        if not product_json:
            return {}

        characteristics = extract_characteristics(soup)
        screen_diagonal, display_resolution = extract_display_info(characteristics)

        images = product_json.get("image") or []
        if isinstance(images, str):
            images = [images]

        offers = normalise_offers(product_json)
        metadata = build_metadata(product_json, offers)
        color, storage = self._guess_color_and_storage(characteristics, product_json)

        data: Dict[str, Any] = {
            "name": product_json.get("name"),
            "product_code": product_json.get("mpn") or metadata.get("sku"),
            "source_url": self.url,
            "price": self._to_decimal(offers.get("price")),
            "sale_price": self._to_decimal(offers.get("sale_price")),
            "manufacturer": extract_brand_name(product_json),
            "color": color,
            "storage": storage,
            "review_count": extract_review_count(product_json, soup),
            "screen_diagonal": screen_diagonal,
            "display_resolution": display_resolution,
            "images": images,
            "characteristics": characteristics,
            "metadata": metadata,
        }

        return {k: v for k, v in data.items() if v not in (None, "")}

    @staticmethod
    def _guess_color_and_storage(
        characteristics: Dict[str, Any],
        product_json: Optional[Dict[str, Any]],
    ) -> Tuple[Optional[str], Optional[str]]:
        color = characteristics.get("Колір") or characteristics.get("Цвет")
        storage = (
            characteristics.get("Вбудована пам'ять")
            or characteristics.get("Объем встроенной памяти")
            or characteristics.get("Пам'ять")
        )

        product_name = product_json.get("name") if product_json else None

        if not color and product_name:
            color_match = _COLOR_PATTERN.search(product_name)
            if color_match:
                color = color_match.group(1)

        if not storage and product_name:
            storage_match = _STORAGE_PATTERN.search(product_name)
            if storage_match:
                storage = storage_match.group(1).upper().replace(" ", "")

        return color, storage

    @staticmethod
    def _to_decimal(value: Any) -> Optional[Decimal]:
        if value is None or value == "":
            return None
        try:
            return Decimal(str(value))
        except (ValueError, ArithmeticError):
            return None


_COLOR_PATTERN = re.compile(
    r"(?i)\b(Black|Blue|White|Silver|Gold|Green|Red|Pink|Purple|Natural Titanium|Blue Titanium|Black Titanium)\b"
)
_STORAGE_PATTERN = re.compile(r"(\d+\s?(?:GB|TB))", re.IGNORECASE)


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

    return "\n".join(lines)

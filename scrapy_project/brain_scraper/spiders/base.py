from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional
from urllib.parse import urljoin

from parsel import Selector

from parser_app.common.constants import (
    ALL_CHARACTERISTICS_BUTTON_XPATH,
    CHARACTERISTICS_KEY_REL_XPATH,
    CHARACTERISTICS_ROWS_XPATH,
    CHARACTERISTICS_VALUE_REL_XPATH,
    COLOR_VALUE_XPATH,
    DISPLAY_RESOLUTION_XPATH,
    IMAGES_XPATH,
    OLD_PRICE_XPATH,
    PRICE_XPATH,
    PRODUCT_CODE_XPATH,
    REVIEW_ANCHOR_XPATH,
    SCREEN_DIAGONAL_XPATH,
    STORAGE_VALUE_XPATH,
)
from parser_app.common.utils import coerce_decimal, extract_int, normalise_space


def _xpath_text(sel: Selector, xpath: str) -> str:
    value = sel.xpath(xpath).xpath("normalize-space(string(.))").get() or ""
    return normalise_space(value)


def _normalise_image_url(base_url: str, src: str) -> str:
    raw = (src or "").strip()
    if not raw:
        return ""
    if raw.startswith("data:"):
        return ""
    if raw.startswith("//"):
        return "https:" + raw
    return urljoin(base_url, raw)


def extract_product_item(
    *,
    selector: Selector,
    source_url: str,
    metadata: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    name = _xpath_text(selector, "//h1[1]")
    product_code = _xpath_text(selector, PRODUCT_CODE_XPATH)
    manufacturer = _xpath_text(selector, "//*[@data-vendor][1]/@data-vendor")

    color = _xpath_text(selector, COLOR_VALUE_XPATH)
    storage = _xpath_text(selector, STORAGE_VALUE_XPATH)
    screen_diagonal = _xpath_text(selector, SCREEN_DIAGONAL_XPATH)
    display_resolution = _xpath_text(selector, DISPLAY_RESOLUTION_XPATH)

    review_anchor_text = _xpath_text(selector, REVIEW_ANCHOR_XPATH)
    review_count = extract_int(review_anchor_text) if review_anchor_text else 0

    price_text = _xpath_text(selector, PRICE_XPATH)
    old_price_text = _xpath_text(selector, OLD_PRICE_XPATH)

    current_price = coerce_decimal(price_text)
    old_price = coerce_decimal(old_price_text)
    price = None
    sale_price = None
    if old_price is not None and current_price is not None:
        price = old_price
        sale_price = current_price
    else:
        price = current_price
        sale_price = None

    images_raw = selector.xpath(IMAGES_XPATH).getall()
    images: List[str] = []
    for src in images_raw:
        resolved = _normalise_image_url(source_url, src)
        if resolved and resolved not in images:
            images.append(resolved)

    characteristics: Dict[str, str] = {}
    for row in selector.xpath(CHARACTERISTICS_ROWS_XPATH):
        key = normalise_space(row.xpath(CHARACTERISTICS_KEY_REL_XPATH).xpath("normalize-space(string(.))").get() or "")
        value = normalise_space(row.xpath(CHARACTERISTICS_VALUE_REL_XPATH).xpath("normalize-space(string(.))").get() or "")
        if key and value:
            characteristics[key] = value

    merged_meta: Dict[str, Any] = {}
    if metadata:
        merged_meta.update(dict(metadata))

    return {
        "name": name,
        "product_code": product_code,
        "source_url": source_url,
        "price": str(price) if price is not None else None,
        "sale_price": str(sale_price) if sale_price is not None else None,
        "manufacturer": manufacturer,
        "color": color,
        "storage": storage,
        "review_count": review_count,
        "screen_diagonal": screen_diagonal,
        "display_resolution": display_resolution,
        "images": images,
        "characteristics": characteristics,
        "metadata": merged_meta,
    }

from __future__ import annotations

from typing import Optional

from core.exceptions import ParserExecutionError
from core.schemas import ProductData

from ...services.parsers import BrainProductParser


def build_product_data(*, url: str, parser_label: str, html: Optional[str] = None) -> ProductData:
    parser = BrainProductParser(url, html=html) if html is not None else BrainProductParser(url)
    raw_payload = parser.parse()
    if not raw_payload:
        raise ParserExecutionError(f"No data returned from {parser_label} parser.")

    product = ProductData.from_mapping(raw_payload)
    product.source_url = url
    return product

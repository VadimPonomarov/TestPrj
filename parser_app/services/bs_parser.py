from typing import Optional

from core.exceptions import ParserExecutionError
from core.schemas import ProductData

from .base import BaseBrainParser
from .brain_parser import BrainProductParser


class BeautifulSoupBrainParser(BaseBrainParser):
    """Adapter around the legacy BeautifulSoup parser."""

    def _parse(self, *, query: Optional[str], url: Optional[str]) -> ProductData:
        if not url:
            raise ParserExecutionError("'url' is required when using the BeautifulSoup parser.")

        parser = BrainProductParser(url)
        raw_payload = parser.parse()
        if not raw_payload:
            raise ParserExecutionError("No data returned from BeautifulSoup parser.")

        product = ProductData.from_mapping(raw_payload)
        product.source_url = url
        return product

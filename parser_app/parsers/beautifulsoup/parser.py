from typing import Optional

from core.exceptions import ParserExecutionError
from core.schemas import ProductData
from ..base.parser import BaseBrainParser
from ..utils.product import build_product_data

class BeautifulSoupBrainParser(BaseBrainParser):
    """Adapter around the legacy BeautifulSoup parser."""

    def _parse(self, *, query: Optional[str], url: Optional[str]) -> ProductData:
        if not url:
            raise ParserExecutionError("'url' is required when using the BeautifulSoup parser.")

        return build_product_data(url=url, parser_label="BeautifulSoup")

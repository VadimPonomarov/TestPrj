from abc import ABC, abstractmethod
from typing import Optional

from core.exceptions import ParserConfigurationError, ParserExecutionError
from core.logging import configure_logger
from core.schemas import ProductData


class BaseBrainParser(ABC):
    """Shared behaviour for brain.com.ua product parsers."""

    def __init__(self) -> None:
        self.logger = configure_logger(f"parser.{self.__class__.__name__}")

    def parse(self, *, query: Optional[str] = None, url: Optional[str] = None) -> ProductData:
        if not query and not url:
            raise ParserConfigurationError("Either 'query' or 'url' must be provided.")

        self.logger.info("Starting parse. query=%s url=%s", query, url)
        try:
            product = self._parse(query=query, url=url)
        except ParserConfigurationError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.exception("Unexpected error during parsing")
            raise ParserExecutionError(str(exc)) from exc

        if not product.product_code:
            raise ParserExecutionError("Parsed product does not contain a product code.")

        self.logger.info("Parsed product '%s' (code=%s)", product.name, product.product_code)
        return product

    @abstractmethod
    def _parse(self, *, query: Optional[str], url: Optional[str]) -> ProductData:
        """Concrete parser implementations must return populated product data."""

from typing import Iterable

import scrapy
from scrapy import Spider
from scrapy.http import Response
from twisted.python.failure import Failure

from core.enums import ParserType
from core.exceptions import ParserExecutionError
from core.schemas import ProductData
from parser_app.services.factory import get_parser

from ..items import ProductItem
from ..utils import resolve_targets


class BrainParserSpider(Spider):
    """Base spider coordinating Scrapy requests with parser backends."""

    parser_type: ParserType = ParserType.BS4
    name = "brain-parser"

    def __init__(self, urls: str | None = None, query: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        config = resolve_targets(self.parser_type, urls, query)
        self.target_urls: list[str] = config.urls
        self.target_query = config.query
        self.start_urls = list(self.target_urls)

    # -- Scrapy hooks -------------------------------------------------
    def start_requests(self) -> Iterable[scrapy.Request]:
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                callback=self.parse_product,
                errback=self.handle_error,
                dont_filter=True,
                cb_kwargs={"target_url": url},
            )

    def handle_error(self, failure: Failure) -> None:
        self.logger.error("Request failed: %s", failure)
        self.crawler.stats.inc_value("brain/product_failures")

    def parse_product(self, response: Response, target_url: str):
        try:
            product = self.run_parser(response=response, target_url=target_url)
        except ParserExecutionError as exc:
            self.logger.error("Parser error for %s: %s", target_url, exc)
            self.crawler.stats.inc_value("brain/parser_errors")
            return

        yield ProductItem.from_product_data(product)
        self.crawler.stats.inc_value("brain/products_parsed")

    # -- Parser integration -------------------------------------------
    def run_parser(self, response: scrapy.http.Response, target_url: str) -> ProductData:
        parser = get_parser(self.parser_type)
        return parser.parse(query=self.target_query, url=target_url)

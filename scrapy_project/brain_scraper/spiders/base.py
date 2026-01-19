import atexit
import os
from typing import Iterable

import scrapy
from scrapy import Spider
from scrapy.http import Response
from twisted.python.failure import Failure
from twisted.internet import reactor
from twisted.internet.threads import deferToThread, deferToThreadPool
from twisted.python.threadpool import ThreadPool

from core.enums import ParserType
from core.exceptions import ParserExecutionError
from core.schemas import ProductData
from parser_app.services.factory import get_parser
from parser_app.parsers.utils.product import build_product_data

from ..items import ProductItem
from ..utils import resolve_targets


def _env_bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if raw == "":
        return default
    try:
        return int(raw)
    except Exception:
        return default


_PLAYWRIGHT_POOL: ThreadPool | None = None
_SELENIUM_POOL: ThreadPool | None = None


def _get_thread_pool(*, name: str, maxthreads: int) -> ThreadPool:
    pool = ThreadPool(minthreads=1, maxthreads=max(1, int(maxthreads)), name=name)
    pool.start()
    return pool


def _get_playwright_pool() -> ThreadPool:
    global _PLAYWRIGHT_POOL
    if _PLAYWRIGHT_POOL is None:
        # Playwright runtime uses a singleton browser with multiple contexts/pages.
        # Allow Scrapy to schedule multiple concurrent parser jobs into that runtime.
        maxthreads = _env_int("SCRAPY_PLAYWRIGHT_CONCURRENT_REQUESTS", 2)
        _PLAYWRIGHT_POOL = _get_thread_pool(name="playwright-parser", maxthreads=maxthreads)
        atexit.register(_PLAYWRIGHT_POOL.stop)
    return _PLAYWRIGHT_POOL


def _get_selenium_pool() -> ThreadPool:
    global _SELENIUM_POOL
    if _SELENIUM_POOL is None:
        # Selenium reuse mode must be serialized (single driver instance).
        _SELENIUM_POOL = _get_thread_pool(name="selenium-parser", maxthreads=1)
        atexit.register(_SELENIUM_POOL.stop)
    return _SELENIUM_POOL


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
        if self.parser_type in {ParserType.SELENIUM, ParserType.PLAYWRIGHT}:
            if self.parser_type == ParserType.PLAYWRIGHT:
                deferred = deferToThreadPool(
                    reactor,
                    _get_playwright_pool(),
                    self.run_parser,
                    response=response,
                    target_url=target_url,
                )
            elif self.parser_type == ParserType.SELENIUM and _env_bool("SELENIUM_REUSE_DRIVER"):
                deferred = deferToThreadPool(
                    reactor,
                    _get_selenium_pool(),
                    self.run_parser,
                    response=response,
                    target_url=target_url,
                )
            else:
                deferred = deferToThread(self.run_parser, response=response, target_url=target_url)

            def _on_success(product: ProductData):
                self.crawler.stats.inc_value("brain/products_parsed")
                return ProductItem.from_product_data(product)

            def _on_error(failure: Failure):
                self.logger.error("Parser error for %s: %s", target_url, failure)
                self.crawler.stats.inc_value("brain/parser_errors")
                return None

            deferred.addCallback(_on_success)
            deferred.addErrback(_on_error)
            return deferred

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
        if self.parser_type == ParserType.BS4:
            html = getattr(response, "text", None)
            if html:
                return build_product_data(url=target_url, html=html, parser_label="BeautifulSoup")
        parser = get_parser(self.parser_type)
        return parser.parse(query=self.target_query, url=target_url)

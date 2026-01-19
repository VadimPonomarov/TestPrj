import os

from core.enums import ParserType

from .base import BrainParserSpider


class BrainSeleniumSpider(BrainParserSpider):
    name = "brain_selenium"
    parser_type = ParserType.SELENIUM

    custom_settings = {
        "DOWNLOAD_DELAY": float(os.getenv("SCRAPY_SELENIUM_DOWNLOAD_DELAY", "1.5")),
        "CONCURRENT_REQUESTS": int(os.getenv("SCRAPY_SELENIUM_CONCURRENT_REQUESTS", "2")),
    }

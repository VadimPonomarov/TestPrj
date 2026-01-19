import os

from core.enums import ParserType

from .base import BrainParserSpider


class BrainPlaywrightSpider(BrainParserSpider):
    name = "brain_playwright"
    parser_type = ParserType.PLAYWRIGHT

    custom_settings = {
        "DOWNLOAD_DELAY": float(os.getenv("SCRAPY_PLAYWRIGHT_DOWNLOAD_DELAY", "2.0")),
        "CONCURRENT_REQUESTS": int(os.getenv("SCRAPY_PLAYWRIGHT_CONCURRENT_REQUESTS", "2")),
    }

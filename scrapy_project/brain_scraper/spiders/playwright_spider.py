from core.enums import ParserType

from .base import BrainParserSpider


class BrainPlaywrightSpider(BrainParserSpider):
    name = "brain_playwright"
    parser_type = ParserType.PLAYWRIGHT

    custom_settings = {
        "DOWNLOAD_DELAY": 2.0,
        "CONCURRENT_REQUESTS": 1,
    }

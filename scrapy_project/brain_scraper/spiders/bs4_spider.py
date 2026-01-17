from core.enums import ParserType

from .base import BrainParserSpider


class BrainBs4Spider(BrainParserSpider):
    name = "brain_bs4"
    parser_type = ParserType.BS4

    custom_settings = {
        "DOWNLOAD_DELAY": 0.5,
        "CONCURRENT_REQUESTS": 4,
    }

from typing import Dict, Type

from core.enums import ParserType

# Import parser implementations from the new parser package
from parser_app.parsers.base.parser import BaseBrainParser
from parser_app.parsers.beautifulsoup.parser import BeautifulSoupBrainParser
from parser_app.parsers.playwright.parser import PlaywrightBrainParser
from parser_app.parsers.selenium.parser import SeleniumBrainParser


_PARSER_REGISTRY: Dict[ParserType, Type[BaseBrainParser]] = {
    ParserType.BS4: BeautifulSoupBrainParser,
    ParserType.SELENIUM: SeleniumBrainParser,
    ParserType.PLAYWRIGHT: PlaywrightBrainParser,
}


def get_parser(parser_type: ParserType) -> BaseBrainParser:
    """Return the parser implementation registered for ``parser_type``."""
    parser_class = _PARSER_REGISTRY.get(parser_type)
    if not parser_class:
        supported = ", ".join(t.value for t in _PARSER_REGISTRY)
        raise ValueError(f"Unsupported parser type: {parser_type}. Supported types: {supported}")

    return parser_class()

from typing import Dict, Type

from core.enums import ParserType

# Import parser implementations from the new parser package
from parser_app.parsers.base.parser import BaseBrainParser


_PARSER_REGISTRY: Dict[ParserType, str] = {
    ParserType.BS4: "parser_app.parsers.beautifulsoup.parser.BeautifulSoupBrainParser",
    ParserType.SELENIUM: "parser_app.parsers.selenium.parser.SeleniumBrainParser",
    ParserType.PLAYWRIGHT: "parser_app.parsers.playwright.parser.PlaywrightBrainParser",
}


def get_parser(parser_type: ParserType) -> BaseBrainParser:
    """Return the parser implementation registered for ``parser_type``."""
    parser_path = _PARSER_REGISTRY.get(parser_type)
    if not parser_path:
        supported = ", ".join(t.value for t in _PARSER_REGISTRY)
        raise ValueError(f"Unsupported parser type: {parser_type}. Supported types: {supported}")

    module_path, _, class_name = parser_path.rpartition(".")
    if not module_path or not class_name:
        raise ValueError(f"Invalid parser registry path for {parser_type}: {parser_path}")

    module = __import__(module_path, fromlist=[class_name])
    parser_class = getattr(module, class_name)
    return parser_class()

from typing import Dict, Type, Union

from core.enums import ParserType
from core.exceptions import ParserConfigurationError

from .base import BaseBrainParser
from .bs_parser import BeautifulSoupBrainParser
from .playwright_parser import PlaywrightBrainParser
from .selenium_parser import SeleniumBrainParser

_PARSER_REGISTRY: Dict[ParserType, Type[BaseBrainParser]] = {
    ParserType.BS4: BeautifulSoupBrainParser,
    ParserType.SELENIUM: SeleniumBrainParser,
    ParserType.PLAYWRIGHT: PlaywrightBrainParser,
}
def get_parser(parser_type: Union[ParserType, str]) -> BaseBrainParser:
    if isinstance(parser_type, str):
        parser_type = ParserType.from_string(parser_type)

    parser_cls = _PARSER_REGISTRY.get(parser_type)
    if not parser_cls:
        raise ParserConfigurationError(f"Parser '{parser_type.value}' is not registered.")

    return parser_cls()

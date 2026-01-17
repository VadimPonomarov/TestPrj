"""
Parser implementations for different technologies.

This package contains various parser implementations for different web technologies:
- BeautifulSoup: For simple HTML parsing
- Selenium: For JavaScript-heavy pages
- Playwright: For modern web applications with complex JavaScript

To use a parser, import it from the appropriate submodule or use the factory:

    from parser_app.factory import get_parser
    
    # Get a parser by type
    parser = get_parser('beautifulsoup')  # or 'selenium', 'playwright'
    
    # Use the parser
    product = parser.parse(url='https://example.com/product/123')
"""

# Import the base parser for type hints
from .base.parser import BaseBrainParser

# Re-export the parser implementations for direct import
from .beautifulsoup.parser import BeautifulSoupBrainParser
from .selenium.parser import SeleniumBrainParser
from .playwright.parser import PlaywrightBrainParser

__all__ = [
    'BaseBrainParser',
    'BeautifulSoupBrainParser',
    'SeleniumBrainParser',
    'PlaywrightBrainParser',
]
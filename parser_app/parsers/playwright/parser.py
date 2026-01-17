from typing import Optional

from core.exceptions import ParserExecutionError
from core.schemas import ProductData
from ..base.parser import BaseBrainParser

# Import from the existing parsers package
from ...services.parsers import BrainProductParser


class PlaywrightBrainParser(BaseBrainParser):
    """Parser implementation using Playwright for JavaScript-heavy pages."""
    
    def _parse(self, *, query: Optional[str], url: Optional[str]) -> ProductData:
        if not url:
            raise ParserExecutionError("'url' is required when using the Playwright parser.")
            
        # Implementation of Playwright parsing logic
        # This is a placeholder - you'll need to implement the actual Playwright logic here
        # or import it from the existing implementation
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                try:
                    page.goto(url, wait_until="networkidle")
                    
                    # Get the page content and pass it to the existing parser
                    content = page.content()

                    # Reuse BrainProductParser with the already fetched HTML to avoid extra requests
                    parser = BrainProductParser(url, html=content)
                    raw_payload = parser.parse()
                    
                    if not raw_payload:
                        raise ParserExecutionError("No data returned from Playwright parser.")
                    
                    product = ProductData.from_mapping(raw_payload)
                    product.source_url = url
                    return product
                    
                finally:
                    browser.close()
                    
        except ImportError:
            raise ParserExecutionError("Playwright is not installed. Please install it with 'pip install playwright' and run 'playwright install'")
        except Exception as e:
            raise ParserExecutionError(f"Error during Playwright parsing: {str(e)}")


# Backwards-compatible alias for package exports expecting PlaywrightParser
PlaywrightParser = PlaywrightBrainParser

import os
import shutil
from typing import Optional

from core.exceptions import ParserExecutionError
from core.schemas import ProductData
from ..base.parser import BaseBrainParser

from ...services.parsers import BrainProductParser


class SeleniumBrainParser(BaseBrainParser):
    """Parser implementation using Selenium for JavaScript-heavy pages."""
    
    def _parse(self, *, query: Optional[str] = None, url: Optional[str] = None) -> ProductData:
        if not url:
            raise ParserExecutionError("'url' is required when using the Selenium parser.")
        
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            
            # Configure Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            driver_path = os.getenv("CHROMEDRIVER_PATH") or shutil.which("chromedriver")
            if not driver_path:
                driver_path = "/usr/bin/chromedriver"

            driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
            
            try:
                # Navigate to the URL
                driver.get(url)
                
                # Wait for the page to load (adjust timeout as needed)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                )

                html = driver.page_source
                parser = BrainProductParser(url, html=html)
                raw_payload = parser.parse()
                if not raw_payload:
                    raise ParserExecutionError("No data returned from Selenium parser.")

                product = ProductData.from_mapping(raw_payload)
                product.source_url = url
                return product
                
            except Exception as e:
                self.logger.error(f"Error during Selenium parsing: {str(e)}")
                raise ParserExecutionError(f"Failed to parse product: {str(e)}")
                
            finally:
                driver.quit()
                
        except ImportError:
            raise ParserExecutionError(
                "Selenium dependencies not found. Please install with: pip install selenium"
            )
        except Exception as e:
            raise ParserExecutionError(f"Unexpected error in Selenium parser: {str(e)}")

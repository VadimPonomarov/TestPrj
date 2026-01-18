"""Scrapy settings for the Brain parsers integration."""

import os
from pathlib import Path

from .django_setup import setup_django

# Ensure Django context is available when Scrapy imports settings
setup_django(os.getenv("DJANGO_SETTINGS_MODULE", "config.settings"))

BASE_DIR = Path(__file__).resolve().parent

BOT_NAME = "brain_scraper"

SPIDER_MODULES = ["brain_scraper.spiders"]
NEWSPIDER_MODULE = "brain_scraper.spiders"

ROBOTSTXT_OBEY = False
DOWNLOAD_DELAY = float(os.getenv("SCRAPY_DOWNLOAD_DELAY", "0.5"))
CONCURRENT_REQUESTS = int(os.getenv("SCRAPY_CONCURRENT_REQUESTS", "4"))
LOG_LEVEL = os.getenv("SCRAPY_LOG_LEVEL", "INFO")

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

ITEM_PIPELINES = {
    "brain_scraper.pipelines.ProductPersistencePipeline": 300,
}

EXTENSIONS = {
    "scrapy.extensions.closespider.CloseSpider": None,
}

_feed_uri = os.getenv("SCRAPY_FEED_URI")
_feed_format = os.getenv("SCRAPY_FEED_FORMAT", "csv")

if _feed_uri:
    FEEDS = {
        _feed_uri: {
            "format": _feed_format,
            "encoding": "utf8",
            "store_empty": False,
            "indent": 2,
        }
    }
else:
    (BASE_DIR.parent / "outputs").mkdir(parents=True, exist_ok=True)
    FEEDS = {
        "outputs/%(name)s_%(time)s.csv": {
            "format": "csv",
            "encoding": "utf8",
            "store_empty": False,
        }
    }

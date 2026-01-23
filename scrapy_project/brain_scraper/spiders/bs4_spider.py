import os
from typing import Iterable, Optional

import scrapy
from parsel import Selector

from core.enums import ParserType
from parser_app.serializers import ProductScrapeRequestSerializer

from .base import extract_product_item


def _split_urls(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    return [u.strip() for u in raw.split(",") if u.strip()]


class BrainBs4Spider(scrapy.Spider):
    name = "brain_bs4"

    custom_settings = {
        "DOWNLOAD_DELAY": float(os.getenv("SCRAPY_BS4_DOWNLOAD_DELAY", "0.5")),
        "CONCURRENT_REQUESTS": int(os.getenv("SCRAPY_BS4_CONCURRENT_REQUESTS", "4")),
    }

    def __init__(self, urls: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        defaults = ProductScrapeRequestSerializer.get_default_payload(ParserType.BS4.value)
        resolved = _split_urls(urls) or ([defaults["url"]] if defaults.get("url") else [])
        if not resolved:
            raise ValueError("At least one URL is required for brain_bs4 spider")
        self.start_urls = list(resolved)

    def start_requests(self) -> Iterable[scrapy.Request]:
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse, dont_filter=True)

    def parse(self, response: scrapy.http.Response):
        selector = Selector(text=getattr(response, "text", "") or "")
        item = extract_product_item(
            selector=selector,
            source_url=response.url,
            metadata={"parser": "ScrapyBS4"},
        )
        yield item

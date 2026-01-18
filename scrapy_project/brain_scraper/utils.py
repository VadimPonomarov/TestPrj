from dataclasses import dataclass
from typing import List, Optional

from core.enums import ParserType
from parser_app.serializers import ProductScrapeRequestSerializer


HOME_URL = "https://brain.com.ua/ukr/"


def _split_urls(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [url.strip() for url in raw.split(",") if url.strip()]


@dataclass
class TargetConfig:
    urls: List[str]
    query: Optional[str]


def resolve_targets(
    parser_type: ParserType,
    urls: Optional[str],
    query: Optional[str],
) -> TargetConfig:
    defaults = ProductScrapeRequestSerializer.get_default_payload(parser_type.value)
    resolved_urls = _split_urls(urls) or ([defaults["url"]] if defaults.get("url") else [])
    resolved_query = query or defaults.get("query")

    if parser_type == ParserType.BS4:
        if not resolved_urls:
            raise ValueError(
                "At least one URL is required for bs4 spider. Pass urls=... or rely on defaults."
            )
    else:
        if not resolved_query:
            raise ValueError(
                "A search query is required for selenium/playwright spiders. Pass query=..."
            )
        if not resolved_urls:
            resolved_urls = [HOME_URL]
    return TargetConfig(urls=resolved_urls, query=resolved_query)

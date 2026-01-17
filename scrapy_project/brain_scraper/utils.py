from dataclasses import dataclass
from typing import List, Optional

from core.enums import ParserType
from parser_app.serializers import ProductScrapeRequestSerializer


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
    if not resolved_urls:
        raise ValueError(
            "At least one URL is required. Provide --set DOWNLOAD_DELAY=... or pass urls parameter."
        )
    return TargetConfig(urls=resolved_urls, query=resolved_query)

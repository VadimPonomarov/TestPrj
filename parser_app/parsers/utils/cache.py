"""Lightweight in-memory cache for resolved product URLs per parser.

The Selenium and Playwright scrapers need to resolve a product URL for the
same query over and over again (admin API triggers often reuse identical
queries).  Hitting the real browser workflow every time is expensive, so we
cache the resolved URL briefly in-process.

This is not intended to be a perfect cache (there is no persistence nor TTL).
It merely prevents back-to-back duplicate requests from paying the full
browser-launch + search penalty.
"""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock
from typing import Optional

_CACHE_CAPACITY = 64
_cache: "OrderedDict[str, str]" = OrderedDict()
_cache_lock = Lock()


def _make_key(parser_name: str, query: str) -> str:
    return f"{parser_name}:{query.strip().lower()}"


def get_cached_url(parser_name: str, query: Optional[str]) -> Optional[str]:
    if not query:
        return None
    key = _make_key(parser_name, query)
    with _cache_lock:
        value = _cache.get(key)
        if value is None:
            return None
        # Promote to most-recent position for basic LRU behaviour.
        _cache.move_to_end(key)
        return value


def set_cached_url(parser_name: str, query: Optional[str], url: Optional[str]) -> None:
    if not query or not url:
        return
    key = _make_key(parser_name, query)
    with _cache_lock:
        _cache[key] = url
        _cache.move_to_end(key)
        while len(_cache) > _CACHE_CAPACITY:
            _cache.popitem(last=False)

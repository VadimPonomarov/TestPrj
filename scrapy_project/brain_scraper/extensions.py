import time

from scrapy import signals


class SpiderTimingExtension:
    def __init__(self, stats):
        self._stats = stats
        self._start_ts: float | None = None

    @classmethod
    def from_crawler(cls, crawler):
        ext = cls(crawler.stats)
        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        return ext

    def spider_opened(self, spider):
        self._start_ts = time.monotonic()
        self._stats.set_value("spider_start_ts", self._start_ts)

    def spider_closed(self, spider, reason):
        if self._start_ts is None:
            return
        elapsed = time.monotonic() - self._start_ts
        self._stats.set_value("spider_elapsed_seconds", elapsed)
        spider.logger.info("[TIMING] Spider %s finished in %.2fs (reason=%s)", spider.name, elapsed, reason)

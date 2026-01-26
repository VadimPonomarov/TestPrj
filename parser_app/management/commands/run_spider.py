import os
import sys
from pathlib import Path

from django.core.management.base import BaseCommand


def _ensure_scrapy_on_path() -> None:
    project_root = Path(__file__).resolve().parents[3]
    scrapy_root = project_root / "scrapy_project"

    for p in (str(project_root), str(scrapy_root)):
        if p not in sys.path:
            sys.path.insert(0, p)

    os.environ.setdefault("SCRAPY_SETTINGS_MODULE", "brain_scraper.settings")


def _parse_spider_args(values: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"Invalid spider argument '{raw}'. Expected key=value.")
        key, value = raw.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid spider argument '{raw}'. Key is empty.")
        parsed[key] = value
    return parsed


class Command(BaseCommand):
    help = "Run a Scrapy spider from scrapy_project via Django manage.py"

    def add_arguments(self, parser):
        parser.add_argument("spider", type=str, help="Spider name (e.g. brain_bs4)")
        parser.add_argument(
            "-a",
            "--arg",
            action="append",
            default=[],
            help="Spider argument in key=value form. Can be provided multiple times.",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="List available spiders and exit (ignores spider name)",
        )

    def handle(self, *args, **options):
        _ensure_scrapy_on_path()

        from scrapy.crawler import CrawlerProcess
        from scrapy.spiderloader import SpiderLoader
        from scrapy.utils.project import get_project_settings

        settings = get_project_settings()

        if options.get("list"):
            loader = SpiderLoader.from_settings(settings)
            names = sorted(loader.list())
            for name in names:
                self.stdout.write(name)
            return

        spider_name: str = str(options["spider"]).strip()
        spider_kwargs = _parse_spider_args(list(options.get("arg") or []))

        process = CrawlerProcess(settings=settings)
        process.crawl(spider_name, **spider_kwargs)
        process.start()

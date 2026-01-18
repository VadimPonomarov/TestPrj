import statistics
import time

from django.core.management.base import BaseCommand

from core.enums import ParserType
from parser_app.parsers.utils import clear_cache
from parser_app.serializers import ProductScrapeRequestSerializer
from parser_app.services.factory import get_parser


class Command(BaseCommand):
    help = "Benchmark product parsers (bs4/selenium/playwright)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--parsers",
            nargs="+",
            default=["bs4", "selenium", "playwright"],
            help="List of parsers to benchmark: bs4 selenium playwright",
        )
        parser.add_argument("--runs", type=int, default=3, help="Number of timed runs")
        parser.add_argument("--warmup", type=int, default=1, help="Number of warmup runs")
        parser.add_argument(
            "--url",
            default=None,
            help="Product URL for bs4 (optional; defaults will be used if omitted)",
        )
        parser.add_argument(
            "--query",
            default=None,
            help="Search query for selenium/playwright (optional; defaults will be used if omitted)",
        )
        parser.add_argument(
            "--cold",
            action="store_true",
            help="Clear in-memory caches between runs (more realistic cold timings)",
        )

    def handle(self, *args, **options):
        parser_names: list[str] = [str(p).strip().lower() for p in options["parsers"]]
        runs: int = options["runs"]
        warmup: int = options["warmup"]
        override_url: str | None = options.get("url")
        override_query: str | None = options.get("query")
        cold: bool = bool(options.get("cold"))

        selected: list[ParserType] = []
        for name in parser_names:
            if name in ("bs4", "beautifulsoup"):
                selected.append(ParserType.BS4)
            elif name in ("selenium",):
                selected.append(ParserType.SELENIUM)
            elif name in ("playwright",):
                selected.append(ParserType.PLAYWRIGHT)
            else:
                raise SystemExit(f"Unknown parser: {name}")

        self.stdout.write("Benchmark configuration:")
        self.stdout.write(f"  parsers: {', '.join(p.value for p in selected)}")
        self.stdout.write(f"  warmup: {warmup}")
        self.stdout.write(f"  runs:   {runs}")
        self.stdout.write("")

        for parser_type in selected:
            try:
                defaults = ProductScrapeRequestSerializer.get_default_payload(parser_type.value)
                url = override_url or defaults.get("url")
                query = override_query or defaults.get("query")

                if parser_type == ParserType.BS4 and not url:
                    raise ValueError("BS4 benchmark requires --url or serializer default url")
                if parser_type in (ParserType.SELENIUM, ParserType.PLAYWRIGHT) and not query:
                    raise ValueError(
                        "Selenium/Playwright benchmark requires --query or serializer default query"
                    )

                parser = get_parser(parser_type)

                def _run_once():
                    if parser_type == ParserType.BS4:
                        parser.parse(url=url)
                    else:
                        parser.parse(query=query)

                if cold:
                    clear_cache()
                for _ in range(max(warmup, 0)):
                    _run_once()

                durations: list[float] = []
                for _ in range(max(runs, 1)):
                    if cold:
                        clear_cache()
                    start = time.perf_counter()
                    _run_once()
                    durations.append(time.perf_counter() - start)

                durations_sorted = sorted(durations)
                p95_index = int(0.95 * (len(durations_sorted) - 1))
                p95 = durations_sorted[p95_index]
                avg = statistics.mean(durations)
                mn = durations_sorted[0]
                mx = durations_sorted[-1]

                self.stdout.write(f"[{parser_type.value}] results:")
                self.stdout.write(f"  min: {mn:.3f}s")
                self.stdout.write(f"  avg: {avg:.3f}s")
                self.stdout.write(f"  p95: {p95:.3f}s")
                self.stdout.write(f"  max: {mx:.3f}s")
                self.stdout.write("")
            except Exception as exc:
                msg = str(exc) or repr(exc)
                self.stdout.write(f"[{parser_type.value}] ERROR: {msg}")
                self.stdout.write("")

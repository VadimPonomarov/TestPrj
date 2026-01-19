import time

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = "Wait for PostgreSQL database to become available"

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout",
            type=int,
            default=60,
            help="Maximum time to wait in seconds (default: 60)",
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=1.0,
            help="Check interval in seconds (default: 1.0)",
        )

    def handle(self, *args, **options):
        timeout = options["timeout"]
        interval = options["interval"]

        self.stdout.write("Waiting for PostgreSQL database...")

        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                self.stdout.write(self.style.ERROR(f"Database connection timeout after {timeout}s"))
                raise SystemExit(1)

            try:
                connection.ensure_connection()
                elapsed_int = int(time.time() - start_time)
                self.stdout.write(self.style.SUCCESS(f"Database is available! (took {elapsed_int}s)"))
                return
            except OperationalError as e:
                elapsed_int = int(elapsed)
                self.stdout.write(f"Database unavailable ({elapsed_int}s/{timeout}s): {e}")
                time.sleep(interval)

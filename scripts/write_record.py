import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.load_django import setup_django


def main() -> None:
    setup_django()
    from parser_app.models import TestRecord

    record = TestRecord.objects.create(title="Hello from script")
    print(f"Created: {record} (id={record.pk})")


if __name__ == "__main__":
    main()

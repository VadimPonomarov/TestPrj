import re
from decimal import Decimal, InvalidOperation
from typing import Any, Optional


def normalise_space(text: str) -> str:
    return " ".join((text or "").split())


def extract_int(text: str) -> int:
    m = re.search(r"(\d+)", text or "")
    return int(m.group(1)) if m else 0


def coerce_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        return value
    try:
        raw = str(value)
        raw = raw.replace("\xa0", " ")
        raw = raw.replace(" ", "")
        raw = raw.replace(",", ".")
        return Decimal(raw)
    except (InvalidOperation, TypeError, ValueError):
        return None

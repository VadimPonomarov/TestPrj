from .constants import *
from .csvio import save_csv_row
from .db import save_product_to_db
from .output import print_mapping
from .overlays import PLAYWRIGHT_OVERLAY_SELECTORS, SELENIUM_OVERLAY_SELECTORS
from .schema import Product
from .utils import coerce_decimal, extract_int, normalise_space


_MANUAL_EXPORTS = {
    "Product",
    "save_csv_row",
    "save_product_to_db",
    "print_mapping",
    "coerce_decimal",
    "extract_int",
    "normalise_space",
    "SELENIUM_OVERLAY_SELECTORS",
    "PLAYWRIGHT_OVERLAY_SELECTORS",
}

_UPPER_CASE_EXPORTS = {
    name
    for name in globals()
    if name.isupper() and not name.startswith("_")
}

__all__ = sorted(_MANUAL_EXPORTS | _UPPER_CASE_EXPORTS)

from typing import Any, Dict

from modules.load_django import setup_django


def save_product_to_db(*, product_code: str, defaults: Dict[str, Any]) -> None:
    setup_django()

    from parser_app.models import Product as ProductModel

    ProductModel.objects.update_or_create(product_code=product_code, defaults=defaults)

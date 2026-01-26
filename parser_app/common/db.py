from typing import Any, Dict

from modules.load_django import setup_django


def save_product_to_db(*, product_code: str, defaults: Dict[str, Any]) -> None:
    setup_django()

    from parser_app.models import Product as ProductModel

    ProductModel.objects.update_or_create(product_code=product_code, defaults=defaults)


def save_product_via_serializer(*, data: Dict[str, Any]) -> None:
    setup_django()

    from django.db import transaction

    from parser_app.models import Product as ProductModel
    from parser_app.serializers import ProductSerializer

    payload: Dict[str, Any] = dict(data)
    for key in ("manufacturer", "color", "storage", "screen_diagonal", "display_resolution"):
        if payload.get(key) in ("", None):
            payload[key] = None

    instance = None
    product_code = payload.get("product_code")
    source_url = payload.get("source_url")

    if product_code:
        instance = ProductModel.objects.filter(product_code=product_code).first()
    if instance is None and source_url:
        instance = ProductModel.objects.filter(source_url=source_url).first()

    serializer = ProductSerializer(instance=instance, data=payload)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        serializer.save()

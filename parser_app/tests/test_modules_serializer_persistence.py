import uuid

import pytest

from parser_app.common.db import save_product_via_serializer
from parser_app.models import Product


@pytest.mark.django_db
def test_modules_save_product_via_serializer_creates_and_is_idempotent():
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "name": f"Module product {suffix}",
        "product_code": f"MOD-{suffix}",
        "source_url": f"https://example.com/module/{suffix}",
        "price": "123.45",
        "sale_price": None,
        "manufacturer": "",
        "color": "",
        "storage": "",
        "review_count": 0,
        "screen_diagonal": "",
        "display_resolution": "",
        "images": [],
        "characteristics": {},
        "metadata": {"parser": "test"},
    }

    save_product_via_serializer(data=payload)
    assert Product.objects.filter(product_code=payload["product_code"]).count() == 1

    save_product_via_serializer(data=payload)
    assert Product.objects.filter(product_code=payload["product_code"]).count() == 1

    obj = Product.objects.get(product_code=payload["product_code"])
    assert obj.source_url == payload["source_url"]
    assert str(obj.price) == "123.45"

from typing import Any, Dict

from django.db import transaction

from parser_app.models import Product
from parser_app.serializers import ProductSerializer


class ProductPersistencePipeline:
    """Persist ProductItem using DRF serializer logic."""

    def process_item(self, item: Dict[str, Any], spider=None):
        product_code = item.get("product_code")
        source_url = item.get("source_url")

        instance = None
        if product_code:
            instance = Product.objects.filter(product_code=product_code).first()
        if instance is None and source_url:
            instance = Product.objects.filter(source_url=source_url).first()

        serializer = ProductSerializer(instance=instance, data=item)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            product = serializer.save()

        if spider is not None:
            spider.logger.info("Persisted product %s", product.product_code)
        return item

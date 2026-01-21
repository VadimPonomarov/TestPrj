from decimal import Decimal
from typing import Any, Mapping, Type, TypeVar, cast

import scrapy

from core.schemas import ProductData
from parser_app.serializers import ProductSerializer


TProductItem = TypeVar("TProductItem", bound="_BaseProductItem")


class _BaseProductItem(scrapy.Item):
    """Scrapy representation of :class:`core.schemas.ProductData`."""

    @classmethod
    def from_product_data(cls: Type[TProductItem], product: ProductData) -> TProductItem:
        item = cls()
        payload: Mapping[str, Any] = product.to_dict()
        for key, value in payload.items():
            if isinstance(value, Decimal):
                value = str(value)
            if key in item.fields:
                item[key] = value
        return item


def serializer_to_item(serializer_cls, *, item_name: str, base_cls: Type[scrapy.Item]) -> Type[scrapy.Item]:
    attrs = {name: scrapy.Field() for name in serializer_cls().fields.keys()}
    return cast(Type[scrapy.Item], type(item_name, (base_cls,), attrs))


ProductItem = serializer_to_item(ProductSerializer, item_name="ProductItem", base_cls=_BaseProductItem)

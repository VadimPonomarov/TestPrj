from decimal import Decimal
from typing import Any, Mapping

import scrapy

from core.schemas import ProductData


class ProductItem(scrapy.Item):
    """Scrapy representation of :class:`core.schemas.ProductData`."""

    name = scrapy.Field()
    product_code = scrapy.Field()
    source_url = scrapy.Field()
    price = scrapy.Field()
    sale_price = scrapy.Field()
    manufacturer = scrapy.Field()
    color = scrapy.Field()
    storage = scrapy.Field()
    review_count = scrapy.Field()
    screen_diagonal = scrapy.Field()
    display_resolution = scrapy.Field()
    images = scrapy.Field()
    characteristics = scrapy.Field()
    metadata = scrapy.Field()

    @classmethod
    def from_product_data(cls, product: ProductData) -> "ProductItem":
        item = cls()
        payload: Mapping[str, Any] = product.to_dict()
        for key, value in payload.items():
            if isinstance(value, Decimal):
                value = str(value)
            item[key] = value
        return item

from rest_framework import serializers

from core.serializers import BaseModelSerializer
from .models import Product


class ProductSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = Product
        fields = [
            "id",
            "name",
            "product_code",
            "source_url",
            "price",
            "sale_price",
            "manufacturer",
            "color",
            "storage",
            "review_count",
            "screen_diagonal",
            "display_resolution",
            "images",
            "characteristics",
            "metadata",
            "created_at",
            "updated_at",
        ]


class ProductScrapeRequestSerializer(serializers.Serializer):
    """Request payload for product scraping endpoint."""

    DEFAULT_PRODUCT_URL = (
        "https://brain.com.ua/ukr/"
        "Mobilniy_telefon_Apple_iPhone_16_Pro_Max_256GB_Black_Titanium-p1145443.html"
    )

    swagger_schema_fields = {
        "example": {
            "url": DEFAULT_PRODUCT_URL
        }
    }
    url = serializers.URLField(
        required=False,
        default=DEFAULT_PRODUCT_URL,
        help_text="Direct product URL from brain.com.ua to scrape.",
    )
    query = serializers.CharField(
        required=False,
        help_text="Fallback search query if direct URL is not provided.",
    )

    def validate(self, attrs):
        if not attrs.get("url") and not attrs.get("query"):
            raise serializers.ValidationError(
                "Either 'url' or 'query' must be provided."
            )
        return attrs

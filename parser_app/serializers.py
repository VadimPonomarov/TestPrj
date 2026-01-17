from rest_framework import serializers

from core.enums import ParserType
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

    DEFAULT_PAYLOADS = {
        ParserType.BS4.value: {
            "url": (
                "https://brain.com.ua/ukr/"
                "Mobilniy_telefon_Apple_iPhone_16_Pro_Max_256GB_Black_Titanium-p1145443.html"
            ),
            "query": "iphone 16 pro max",
        },
        ParserType.SELENIUM.value: {
            "url": (
                "https://brain.com.ua/ukr/"
                "Mobilniy_telefon_Samsung_Galaxy_S24_Ultra_512GB_Black-p1264325.html"
            ),
            "query": "samsung galaxy s24 ultra",
        },
        ParserType.PLAYWRIGHT.value: {
            "url": (
                "https://brain.com.ua/ukr/"
                "Mobilniy_telefon_Xiaomi_14_Pro_512GB_Black-p1261533.html"
            ),
            "query": "xiaomi 14 pro",
        },
    }

    url = serializers.URLField(
        required=False,
        help_text="Direct product URL from brain.com.ua to scrape.",
    )
    query = serializers.CharField(
        required=False,
        help_text="Fallback search query if direct URL is not provided.",
    )

    def __init__(self, *args, **kwargs):
        self.parser_type = self._resolve_parser_type(
            (kwargs.get("context") or {}).get("parser_type")
        )
        super().__init__(*args, **kwargs)
        defaults = self.get_default_payload(self.parser_type)
        default_url = defaults.get("url")
        default_query = defaults.get("query")
        if default_url:
            self.fields["url"].default = default_url
            self.fields["url"].initial = default_url
        if default_query:
            self.fields["query"].default = default_query
            self.fields["query"].initial = default_query

    @classmethod
    def _resolve_parser_type(cls, parser_type):
        if isinstance(parser_type, ParserType):
            return parser_type.value
        if not parser_type:
            return ParserType.BS4.value
        try:
            return ParserType.from_string(parser_type).value
        except ValueError:
            return ParserType.BS4.value

    @classmethod
    def get_default_payload(cls, parser_type=None):
        parser_type_value = cls._resolve_parser_type(parser_type)
        defaults = cls.DEFAULT_PAYLOADS.get(parser_type_value) or {}
        return dict(defaults)

    def validate(self, attrs):
        if not attrs.get("url") and not attrs.get("query"):
            raise serializers.ValidationError(
                "Either 'url' or 'query' must be provided."
            )
        return attrs

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
        extra_kwargs = {
            **getattr(BaseModelSerializer.Meta, "extra_kwargs", {}),
            "price": {"required": False, "allow_null": True},
            "sale_price": {"required": False, "allow_null": True},
            "manufacturer": {"required": False, "allow_blank": True},
            "color": {"required": False, "allow_blank": True},
            "storage": {"required": False, "allow_blank": True},
            "review_count": {"required": False},
            "screen_diagonal": {"required": False, "allow_blank": True},
            "display_resolution": {"required": False, "allow_blank": True},
            "images": {"required": False, "allow_null": True},
            "characteristics": {"required": False, "allow_null": True},
            "metadata": {"required": False, "allow_null": True},
        }


class ProductScrapeRequestSerializer(serializers.Serializer):
    """Request payload for product scraping endpoint."""

    DEFAULT_PAYLOADS = {
        ParserType.BS4.value: {
            "url": (
                "https://brain.com.ua/ukr/"
                "Mobilniy_telefon_Apple_iPhone_16_Pro_Max_256GB_Black_Titanium-p1145443.html"
            )
        },
        ParserType.SELENIUM.value: {
            "query": "Apple iPhone 15 128GB Black",
        },
        ParserType.PLAYWRIGHT.value: {
            "query": "Apple iPhone 15 128GB Black",
        },
    }

    url = serializers.URLField(
        required=False,
        help_text="Повний URL конкретного товару на brain.com.ua.",
    )
    query = serializers.CharField(
        required=False,
        help_text="Пошуковий запит на brain.com.ua (динамічний параметр).",
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

    def validate(self, attrs):
        parser_type = self._resolve_parser_type(self.parser_type)
        url = attrs.get("url")
        query = attrs.get("query")

        if parser_type == ParserType.BS4.value:
            if not url:
                raise serializers.ValidationError(
                    {"url": "Для BeautifulSoup парсера необхідно передати URL товару."}
                )
            if query:
                raise serializers.ValidationError(
                    {"query": "Параметр query не використовується у bs4 режимі."}
                )
        else:
            if not query:
                raise serializers.ValidationError(
                    {"query": "Для Selenium/Playwright потрібно вказати пошуковий запит."}
                )
        return attrs

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

    @classmethod
    def get_default_url(cls, parser_type=None):
        payload = cls.get_default_payload(parser_type)
        return payload.get("url")

import json
import os

from django.conf import settings
from django.http import FileResponse
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response

import pandas as pd

from core.enums import ParserType
from core.schemas import ProductData

from .models import Product
from .serializers import ProductSerializer
from .services.factory import get_parser
from .services.brain_parser import format_product_output


class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all().order_by("-created_at")
    serializer_class = ProductSerializer


class ProductRetrieveView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class ProductScrapeView(generics.CreateAPIView):
    """Create or update a product by scraping data from brain.com.ua."""

    serializer_class = ProductSerializer
    queryset = Product.objects.all()

    def create(self, request, *args, **kwargs):
        parser_type_kwarg = kwargs.get("parser_type")
        parser_type_raw = parser_type_kwarg or request.data.get("parser", ParserType.BS4.value)
        try:
            parser_type = ParserType.from_string(parser_type_raw)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        url = request.data.get("url")
        query = request.data.get("query")
        if not url and not query:
            return Response(
                {"detail": "Необходимо указать либо 'url', либо 'query'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        parser = get_parser(parser_type)
        try:
            product_payload: ProductData = parser.parse(query=query, url=url)
        except Exception as exc:  # pragma: no cover - handled by parser logging
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        printable = format_product_output(product_payload.to_dict())
        parser.logger.info("Parsed product:\n%s", printable)

        payload = product_payload.to_model_payload()
        product, created = Product.objects.update_or_create(
            product_code=payload.pop("product_code"),
            defaults=payload,
        )

        serializer = self.get_serializer(product)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            headers=headers,
        )


class ProductExportCsvView(generics.ListAPIView):
    """Export all products to CSV."""

    queryset = Product.objects.all().order_by("-created_at")
    serializer_class = ProductSerializer

    def get(self, request, *args, **kwargs):
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

        queryset = self.get_queryset().values(*fields)
        records = []
        for product in queryset:
            record = {}
            for field in fields:
                value = product.get(field)
                if field in {"images", "characteristics", "metadata"} and value not in (None, ""):
                    value = json.dumps(value, ensure_ascii=False)
                if field in {"created_at", "updated_at"} and value is not None:
                    value = value.isoformat()
                record[field] = value
            records.append(record)

        df = pd.DataFrame(records, columns=fields)

        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"products_{timestamp}.csv"
        temp_file_path = os.path.join(settings.TEMP_DIR, file_name)

        df.to_csv(temp_file_path, index=False)

        file_handle = open(temp_file_path, "rb")
        return FileResponse(file_handle, as_attachment=True, filename=file_name)

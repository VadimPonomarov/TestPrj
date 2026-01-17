import json
import os

from django.conf import settings
from django.http import FileResponse
from django.utils import timezone
from rest_framework import generics, status, filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema

from .filters import ProductFilter
from rest_framework.response import Response

import pandas as pd

from core.enums import ParserType
from core.schemas import ProductData

from .models import Product
from .pagination import CustomPagination
from .serializers import ProductSerializer, ProductScrapeRequestSerializer
from .services.factory import get_parser
from .services.parsers import format_product_output


class ProductListCreateView(generics.ListCreateAPIView):
    """
    View for listing and creating products with filtering and pagination.
    
    Filtering:
    - Search: /?search=query (searches in name, product_code, manufacturer, characteristics)
    - Price range: /?min_price=100&max_price=1000
    - Exact match: /?name=exact_name
    - Contains: /?name__icontains=partial_name
    - Greater than: /?price__gt=100
    - Less than: /?price__lt=1000
    
    Ordering:
    - /?ordering=field (ascending)
    - /?ordering=-field (descending)
    Available fields: name, price, created_at, updated_at
    
    Pagination:
    - /?page=2
    - /?page=2&page_size=50
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ProductFilter
    pagination_class = CustomPagination
    ordering_fields = ['name', 'price', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return super().get_queryset().order_by('-created_at')

    @swagger_auto_schema(responses={200: ProductSerializer(many=True)})
    def get(self, *args, **kwargs):  # type: ignore[override]
        return super().get(*args, **kwargs)

    @swagger_auto_schema(request_body=ProductSerializer, responses={201: ProductSerializer, 200: ProductSerializer})
    def post(self, *args, **kwargs):  # type: ignore[override]
        return super().post(*args, **kwargs)


class ProductRetrieveView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @swagger_auto_schema(responses={200: ProductSerializer})
    def get(self, *args, **kwargs):  # type: ignore[override]
        return super().get(*args, **kwargs)


class ProductScrapeView(generics.CreateAPIView):
    """Create or update a product by scraping data from brain.com.ua."""

    serializer_class = ProductSerializer
    queryset = Product.objects.all()

    @swagger_auto_schema(
        request_body=ProductScrapeRequestSerializer,
        responses={200: ProductSerializer, 201: ProductSerializer},
        operation_summary="Scrape product data",
        operation_description=(
            "Trigger scraping for a brain.com.ua product using the selected parser backend and "
            "return the resulting product instance."
        ),
    )
    def create(self, request, *args, **kwargs):
        serializer = ProductScrapeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        parser_type_kwarg = kwargs.get("parser_type")
        validated = serializer.validated_data
        parser_type_raw = parser_type_kwarg or validated.get("parser", ParserType.BS4.value)
        try:
            parser_type = ParserType.from_string(parser_type_raw)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        url = validated.get("url")
        query = validated.get("query")
        if not url and not query:
            return Response(
                {"detail": "Either 'url' or 'query' must be provided."},
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
    """Export filtered products to CSV."""
    
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ProductFilter
    
    def get_queryset(self):
        return Product.objects.all().order_by("-created_at")

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

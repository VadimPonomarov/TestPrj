import json
import os

from django.conf import settings
from django.http import FileResponse
from django.utils import timezone
from rest_framework import generics, status, filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.inspectors import SwaggerAutoSchema
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


class ProductListSchema(SwaggerAutoSchema):
    def get_query_parameters(self):
        params = list(super().get_query_parameters())

        ordering_enum = []
        for field in getattr(self.view, "ordering_fields", []) or []:
            ordering_enum.append(field)
            ordering_enum.append(f"-{field}")

        page_size_enum = [10, 20, 50, 100]

        updated = []
        for p in params:
            if p.name == "ordering":
                updated.append(
                    openapi.Parameter(
                        name="ordering",
                        in_=openapi.IN_QUERY,
                        type=openapi.TYPE_STRING,
                        description=p.description or "Ordering of results.",
                        required=False,
                        enum=ordering_enum or None,
                    )
                )
                continue

            if p.name == "page_size":
                updated.append(
                    openapi.Parameter(
                        name="page_size",
                        in_=openapi.IN_QUERY,
                        type=openapi.TYPE_INTEGER,
                        description=p.description or "Number of items per page.",
                        required=False,
                        enum=page_size_enum,
                    )
                )
                continue

            updated.append(p)

        return updated


class ProductScrapeSchema(SwaggerAutoSchema):
    def get_path_parameters(self):
        params = list(super().get_path_parameters())
        parser_enum = [choice.value for choice in ParserType]

        updated = []
        for p in params:
            if p.name == "parser_type":
                updated.append(
                    openapi.Parameter(
                        name="parser_type",
                        in_=openapi.IN_PATH,
                        type=openapi.TYPE_STRING,
                        required=True,
                        description="Parser backend to execute.",
                        enum=parser_enum,
                    )
                )
            else:
                updated.append(p)

        return updated


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
    swagger_schema = ProductListSchema
    
    def get_queryset(self):
        return super().get_queryset().order_by('-created_at')

    @swagger_auto_schema(
        operation_summary="List products",
        operation_description="List products with filtering, ordering and pagination.",
        tags=["Products"],
        responses={200: ProductSerializer(many=True)},
    )
    def get(self, *args, **kwargs):  # type: ignore[override]
        return super().get(*args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create product",
        operation_description="Create a product record.",
        tags=["Products"],
        request_body=ProductSerializer,
        responses={201: ProductSerializer, 200: ProductSerializer},
    )
    def post(self, *args, **kwargs):  # type: ignore[override]
        return super().post(*args, **kwargs)


class ProductRetrieveView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @swagger_auto_schema(
        operation_summary="Retrieve product",
        operation_description="Retrieve a single product by id.",
        tags=["Products"],
        responses={200: ProductSerializer},
    )
    def get(self, *args, **kwargs):  # type: ignore[override]
        return super().get(*args, **kwargs)


class ProductScrapeView(generics.CreateAPIView):
    """Create or update a product by scraping data from brain.com.ua."""

    serializer_class = ProductSerializer
    queryset = Product.objects.all()
    swagger_schema = ProductScrapeSchema

    @swagger_auto_schema(
        request_body=ProductScrapeRequestSerializer,
        responses={200: ProductSerializer, 201: ProductSerializer},
        operation_summary="Scrape product",
        operation_description=(
            "Trigger scraping for a brain.com.ua product using the selected parser backend and "
            "return the resulting product instance."
        ),
        tags=["Scrappers"],
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = ProductScrapeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        parser_type_kwarg = kwargs.get("parser_type")
        validated = serializer.validated_data
        parser_type_raw = parser_type_kwarg or ParserType.BS4.value
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

        missing = []
        required_str_fields = {
            "name": product_payload.name,
            "product_code": product_payload.product_code,
            "source_url": product_payload.source_url,
        }
        for field_name, value in required_str_fields.items():
            if not value:
                missing.append(field_name)

        if product_payload.price is None:
            missing.append("price")

        if missing:
            return Response(
                {
                    "detail": "Parsed product is missing required fields.",
                    "missing": missing,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        missing_optional = []
        optional_fields = {
            "manufacturer": product_payload.manufacturer,
            "color": product_payload.color,
            "storage": product_payload.storage,
            "screen_diagonal": product_payload.screen_diagonal,
            "display_resolution": product_payload.display_resolution,
        }
        for field_name, value in optional_fields.items():
            if not value:
                missing_optional.append(field_name)

        if not product_payload.images:
            missing_optional.append("images")
        if not product_payload.characteristics:
            missing_optional.append("characteristics")

        if missing_optional:
            parser.logger.info("Missing optional fields: %s", ", ".join(missing_optional))

        printable = format_product_output(product_payload.to_dict())
        parser.logger.info("Parsed product:\n%s", printable)

        update_payload = product_payload.to_model_payload()
        product_code = update_payload.pop("product_code")
        try:
            product = Product.objects.get(product_code=product_code)
        except Product.DoesNotExist:
            created = True
            create_payload = product_payload.to_dict()
            create_payload.pop("product_code", None)
            product = Product.objects.create(product_code=product_code, **create_payload)
        else:
            created = False
            for key, value in update_payload.items():
                setattr(product, key, value)
            product.save()

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
    swagger_schema = ProductListSchema
    
    def get_queryset(self):
        return Product.objects.all().order_by("-created_at")

    @swagger_auto_schema(
        operation_summary="Export products to CSV",
        operation_description="Export products to a CSV file (supports the same filters as listing).",
        tags=["Export"],
        responses={200: "CSV file"},
    )
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

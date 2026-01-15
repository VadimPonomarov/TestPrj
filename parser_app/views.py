import csv
import json

from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.response import Response

from .models import Product
from .serializers import ProductSerializer
from .services.brain_parser import BrainProductParser, format_product_output


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
        url = request.data.get("url")
        if not url:
            return Response({"detail": "Поле 'url' обязательно."}, status=status.HTTP_400_BAD_REQUEST)

        parser = BrainProductParser(url)
        product_data = parser.parse()

        if not product_data:
            return Response({"detail": "Не удалось разобрать страницу товара."}, status=status.HTTP_400_BAD_REQUEST)

        product_code = product_data.get("product_code")
        if not product_code:
            return Response({"detail": "Код товара не найден на странице."}, status=status.HTTP_400_BAD_REQUEST)

        # Print parsed data for debugging/logging (Step 3 requirement)
        print(format_product_output(product_data))

        product_defaults = product_data.copy()
        product_defaults.pop("product_code", None)

        product, created = Product.objects.update_or_create(
            product_code=product_code,
            defaults=product_defaults,
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

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="products.csv"'

        writer = csv.writer(response)
        writer.writerow(fields)

        for product in self.get_queryset():
            row = []
            for field in fields:
                value = getattr(product, field)
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                row.append(value)
            writer.writerow(row)

        return response

from django.urls import path

from .views import (
    ProductExportCsvView,
    ProductListCreateView,
    ProductRetrieveView,
    ProductScrapeView,
)

urlpatterns = [
    path("products/", ProductListCreateView.as_view(), name="product-list"),
    path("products/<int:pk>/", ProductRetrieveView.as_view(), name="product-detail"),
    path("products/<str:parser_type>/scrape/", ProductScrapeView.as_view(), name="product-scrape"),
    path("products/export-csv/", ProductExportCsvView.as_view(), name="product-export-csv"),
]

from django.urls import path

from .views import (
    ProductExportCsvView,
    ProductListCreateView,
    ProductRetrieveView,
    ProductScrapeBS4View,
    ProductScrapePlaywrightView,
    ProductScrapeSeleniumView,
)

urlpatterns = [
    path("products/", ProductListCreateView.as_view(), name="product-list"),
    path("products/<int:pk>/", ProductRetrieveView.as_view(), name="product-detail"),
    path("products/scrape/bs4/", ProductScrapeBS4View.as_view(), name="product-scrape-bs4"),
    path("products/scrape/selenium/", ProductScrapeSeleniumView.as_view(), name="product-scrape-selenium"),
    path("products/scrape/playwright/", ProductScrapePlaywrightView.as_view(), name="product-scrape-playwright"),
    path("products/export-csv/", ProductExportCsvView.as_view(), name="product-export-csv"),
]

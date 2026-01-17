"""Swagger and ReDoc documentation endpoints."""

import os

from django.urls import path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="TestPrj API",
        default_version="v1",
        description="""
        # 🧩 TestPrj API Documentation

        Complete API documentation for the TestPrj parser service with interactive Swagger UI.

        ## 📋 API Organization

        The API is organized into logical groups using standardized tags:

        ### Products
        - **Products** - List, create, retrieve products with filtering and pagination

        ### Scrappers
        - **Scrappers** - Trigger product scraping using the selected parser backend

        ### Export
        - **Export** - Export filtered product data to CSV
        """,
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="pvs.versia@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    url=os.getenv("SWAGGER_DEFAULT_API_URL", "http://localhost"),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("api/doc/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("api/redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    re_path(r"^api/doc(?P<format>\.json|\.yaml)$", schema_view.without_ui(cache_timeout=0), name="schema-json"),
]

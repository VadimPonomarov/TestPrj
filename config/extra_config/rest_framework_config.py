"""Django REST framework configuration."""

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "parser_app.pagination.CustomPagination",
    "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

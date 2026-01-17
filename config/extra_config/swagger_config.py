"""Swagger/OpenAPI configuration for TestPrj."""

import os


SWAGGER_GENERATOR_CLASS = "config.docs.swagger_generator.CustomOpenAPISchemaGenerator"


def get_swagger_settings() -> dict:
    """Return Swagger UI configuration."""
    environment = os.getenv("DJANGO_ENV", "development")
    is_production = environment == "production"

    return {
        "SECURITY_DEFINITIONS": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
            }
        },
        "USE_SESSION_AUTH": False,
        "JSON_EDITOR": True,
        "SUPPORTED_SUBMIT_METHODS": ["get", "post", "put", "delete", "patch"],
        "DOC_EXPANSION": "none",
        "OPERATIONS_SORTER": "alpha",
        "TAGS_SORTER": "alpha",
        "DEEP_LINKING": True,
        "SHOW_EXTENSIONS": True,
        "DEFAULT_MODEL_RENDERING": "model",
        "DEFAULT_MODEL_DEPTH": 3,
        "VALIDATOR_URL": None if is_production else "https://validator.swagger.io/validator",
        "PERSIST_AUTH": True,
        "DISPLAY_OPERATION_ID": False,
        "REFETCH_SCHEMA_WITH_AUTH": True,
        "REFETCH_SCHEMA_ON_LOGOUT": True,
        "DEFAULT_API_URL": os.getenv("SWAGGER_DEFAULT_API_URL", "http://localhost"),
        "DEFAULT_GENERATOR_CLASS": SWAGGER_GENERATOR_CLASS,
        "TAGS": [
            {"name": "Products", "description": "List, create, retrieve products"},
            {"name": "Scrappers", "description": "Trigger scraping using the selected parser backend"},
            {"name": "Export", "description": "Export filtered product data to CSV"},
        ],
    }


SWAGGER_SETTINGS = get_swagger_settings()
SWAGGER_USE_SESSION_AUTH = False

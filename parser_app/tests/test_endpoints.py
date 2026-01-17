import uuid
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from core.schemas import ProductData
from parser_app.models import Product


@pytest.fixture()
def api_client():
    return APIClient()


@pytest.fixture()
def product_payload():
    return {
        "name": "Test product",
        "product_code": "CODE-1",
        "source_url": "https://example.com/products/1",
        "price": "123.45",
    }


@pytest.fixture()
def product_factory():
    def _create(**overrides):
        suffix = uuid.uuid4().hex[:6]
        defaults = {
            "name": f"Factory product {suffix}",
            "product_code": f"FACT-{suffix}",
            "source_url": f"https://example.com/factory/{suffix}",
            "price": Decimal("199.99"),
            "sale_price": Decimal("149.99"),
        }
        defaults.update(overrides)
        return Product.objects.create(**defaults)

    return _create


@pytest.mark.django_db
def test_products_list_empty(api_client):
    url = reverse("product-list")
    resp = api_client.get(url)
    assert resp.status_code == 200
    assert resp.data["count"] == 0
    assert resp.data["results"] == []


@pytest.mark.django_db
def test_products_create_and_retrieve(api_client, product_payload):
    list_url = reverse("product-list")

    create_resp = api_client.post(list_url, data=product_payload, format="json")
    assert create_resp.status_code == 201
    product_id = create_resp.data["id"]

    detail_url = reverse("product-detail", kwargs={"pk": product_id})
    detail_resp = api_client.get(detail_url)
    assert detail_resp.status_code == 200
    assert detail_resp.data["id"] == product_id
    assert detail_resp.data["product_code"] == product_payload["product_code"]


@pytest.mark.django_db
def test_products_list_with_pagination(api_client, product_payload):
    list_url = reverse("product-list")

    for i in range(3):
        payload = dict(product_payload)
        payload["product_code"] = f"CODE-{i + 1}"
        payload["source_url"] = f"https://example.com/products/{i + 1}"
        payload["name"] = f"Test product {i + 1}"
        resp = api_client.post(list_url, data=payload, format="json")
        assert resp.status_code == 201

    resp = api_client.get(list_url, data={"page_size": 2})
    assert resp.status_code == 200
    assert resp.data["count"] == 3
    assert resp.data["page_size"] == 2
    assert len(resp.data["results"]) == 2


@pytest.mark.django_db
def test_products_filter_search_and_price_range(api_client, product_factory):
    list_url = reverse("product-list")
    product_factory(
        name="Gaming Laptop",
        product_code="LAP-100",
        manufacturer="BrandA",
        price=Decimal("1399.99"),
    )
    product_factory(
        name="Office Laptop",
        product_code="LAP-200",
        manufacturer="BrandB",
        price=Decimal("899.99"),
    )

    resp = api_client.get(
        list_url,
        data={"search": "Gaming", "min_price": "1200", "ordering": "-price"},
    )
    assert resp.status_code == 200
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["product_code"] == "LAP-100"


@pytest.mark.django_db
def test_products_ordering_by_price(api_client, product_factory):
    list_url = reverse("product-list")
    product_factory(product_code="LAP-100", price=Decimal("999.99"))
    product_factory(product_code="LAP-200", price=Decimal("499.99"))

    resp = api_client.get(list_url, data={"ordering": "price", "page_size": 10})
    assert resp.status_code == 200
    codes = [item["product_code"] for item in resp.data["results"]]
    assert codes == ["LAP-200", "LAP-100"]


@pytest.mark.django_db
def test_products_create_validation_error(api_client):
    list_url = reverse("product-list")
    resp = api_client.post(list_url, data={"name": "Invalid"}, format="json")
    assert resp.status_code == 400
    assert "product_code" in resp.data


@pytest.mark.django_db
def test_export_csv(api_client, settings, tmp_path, product_payload):
    settings.TEMP_DIR = str(tmp_path)

    list_url = reverse("product-list")
    resp = api_client.post(list_url, data=product_payload, format="json")
    assert resp.status_code == 201

    export_url = reverse("product-export-csv")
    export_resp = api_client.get(export_url)
    assert export_resp.status_code == 200
    assert "attachment" in export_resp.get("Content-Disposition", "")


@pytest.mark.django_db
def test_scrape_requires_url_or_query(api_client):
    url = reverse("product-scrape", kwargs={"parser_type": "bs4"})
    resp = api_client.post(url, data={"url": ""}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_scrape_invalid_parser_type(api_client):
    url = reverse("product-scrape", kwargs={"parser_type": "invalid"})
    resp = api_client.post(
        url,
        data={"url": "https://example.com/products/invalid"},
        format="json",
    )
    assert resp.status_code == 400
    assert "detail" in resp.data


@pytest.mark.django_db
def test_scrape_accepts_empty_body_and_uses_default_url(api_client, mocker):
    logger = mocker.Mock()

    class _Parser:
        pass

        def parse(self, query=None, url=None):
            assert url
            return ProductData(
                name="Default url product",
                product_code="DEFAULT-1",
                source_url=url,
                price=Decimal("10.00"),
            )

    parser = _Parser()
    parser.logger = logger
    mocker.patch("parser_app.views.get_parser", return_value=parser)
    mocker.patch("parser_app.views.format_product_output", return_value="")

    url = reverse("product-scrape", kwargs={"parser_type": "bs4"})
    resp = api_client.post(url, data={}, format="json")
    assert resp.status_code in (200, 201)
    assert resp.data["product_code"] == "DEFAULT-1"


@pytest.mark.django_db
def test_scrape_creates_or_updates_product(api_client, mocker):
    class _Logger:
        def info(self, *args, **kwargs):
            return None

    class _Parser:
        logger = _Logger()

        def parse(self, query=None, url=None):
            return ProductData(
                name="Scraped product",
                product_code="SCRAPED-1",
                source_url=url or "https://example.com/scraped",
                manufacturer="Apple",
                color="Black",
                storage="128GB",
                price=Decimal("999.99"),
                sale_price=Decimal("899.99"),
                review_count=7,
                screen_diagonal="6.1",
                display_resolution="2556x1179",
                images=["https://example.com/img1.jpg"],
                characteristics={"Колір": "Black", "Пам'ять": "128GB"},
                metadata={"sku": "SCRAPED-1"},
            )

    mocker.patch("parser_app.views.get_parser", return_value=_Parser())
    mocker.patch("parser_app.views.format_product_output", return_value="")

    url = reverse("product-scrape", kwargs={"parser_type": "bs4"})
    resp = api_client.post(
        url, data={"url": "https://example.com/scraped"}, format="json"
    )
    assert resp.status_code in (200, 201)
    assert resp.data["product_code"] == "SCRAPED-1"

    list_url = reverse("product-list")
    list_resp = api_client.get(list_url)
    assert list_resp.status_code == 200
    assert list_resp.data["count"] == 1


@pytest.mark.django_db
@pytest.mark.parametrize("parser_type", ["bs4", "selenium", "playwright"])
def test_scrape_success_for_all_parsers(api_client, mocker, parser_type):
    class _Logger:
        def info(self, *args, **kwargs):
            return None

    class _Parser:
        logger = _Logger()

        def parse(self, query=None, url=None):
            return ProductData(
                name="Scraped product",
                product_code=f"SCRAPED-{parser_type}",
                source_url=url or "https://example.com/scraped",
                manufacturer="Apple",
                color="Black",
                storage="128GB",
                price=Decimal("999.99"),
                sale_price=Decimal("899.99"),
                review_count=7,
                screen_diagonal="6.1",
                display_resolution="2556x1179",
                images=["https://example.com/img1.jpg"],
                characteristics={"Колір": "Black", "Пам'ять": "128GB"},
                metadata={"sku": "SCRAPED"},
            )

    mocker.patch("parser_app.views.get_parser", return_value=_Parser())
    mocker.patch("parser_app.views.format_product_output", return_value="")

    url = reverse("product-scrape", kwargs={"parser_type": parser_type})
    resp = api_client.post(url, data={"url": "https://example.com/scraped"}, format="json")
    assert resp.status_code in (200, 201)
    assert resp.data["manufacturer"] == "Apple"
    assert resp.data["images"]
    assert resp.data["characteristics"]


@pytest.mark.django_db
@pytest.mark.parametrize("parser_type", ["bs4", "selenium", "playwright"])
def test_scrape_rejects_incomplete_payload_and_does_not_write_db(api_client, mocker, parser_type):
    logger = mocker.Mock()

    class _Parser:
        pass

        def parse(self, query=None, url=None):
            return ProductData(product_code="INC-1", source_url=url or "https://example.com/incomplete")

    parser = _Parser()
    parser.logger = logger
    mocker.patch("parser_app.views.get_parser", return_value=parser)

    url = reverse("product-scrape", kwargs={"parser_type": parser_type})
    resp = api_client.post(url, data={"url": "https://example.com/incomplete"}, format="json")
    assert resp.status_code == 400
    assert resp.data["detail"] == "Parsed product is missing required fields."
    assert "missing" in resp.data
    assert Product.objects.filter(product_code="INC-1").count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("parser_type", ["bs4", "selenium", "playwright"])
def test_scrape_requires_price_and_does_not_write_db(api_client, mocker, parser_type):
    logger = mocker.Mock()

    class _Parser:
        pass

        def parse(self, query=None, url=None):
            return ProductData(
                name="No price",
                product_code="NOPRICE-1",
                source_url=url or "https://example.com/noprice",
                price=None,
            )

    parser = _Parser()
    parser.logger = logger
    mocker.patch("parser_app.views.get_parser", return_value=parser)
    url = reverse("product-scrape", kwargs={"parser_type": parser_type})
    resp = api_client.post(url, data={"url": "https://example.com/noprice"}, format="json")
    assert resp.status_code == 400
    assert resp.data["detail"] == "Parsed product is missing required fields."
    assert "price" in resp.data.get("missing", [])
    assert Product.objects.filter(product_code="NOPRICE-1").count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("parser_type", ["bs4", "selenium", "playwright"])
def test_scrape_allows_optional_fields_missing_and_persists_defaults_on_create(api_client, mocker, parser_type):
    logger = mocker.Mock()

    class _Parser:
        pass

        def parse(self, query=None, url=None):
            return ProductData(
                name="Partial",
                product_code=f"PARTIAL-{parser_type}",
                source_url=url or "https://example.com/partial",
                price=Decimal("1.00"),
            )

    parser = _Parser()
    parser.logger = logger
    mocker.patch("parser_app.views.get_parser", return_value=parser)
    mocker.patch("parser_app.views.format_product_output", return_value="")

    url = reverse("product-scrape", kwargs={"parser_type": parser_type})
    resp = api_client.post(url, data={"url": "https://example.com/partial"}, format="json")
    assert resp.status_code in (200, 201)
    assert resp.data["name"] == "Partial"
    assert resp.data["product_code"] == f"PARTIAL-{parser_type}"
    assert resp.data["source_url"] == "https://example.com/partial"
    assert resp.data["review_count"] == 0
    assert logger.info.call_count >= 1
    assert any(
        (call.args and call.args[0] == "Missing optional fields: %s")
        for call in logger.info.call_args_list
    )


@pytest.mark.django_db
def test_scrape_parser_exception_handled(api_client, mocker):
    class _Logger:
        def info(self, *args, **kwargs):
            return None

    class _Parser:
        logger = _Logger()

        def parse(self, query=None, url=None):
            raise RuntimeError("Parser failed")

    mocker.patch("parser_app.views.get_parser", return_value=_Parser())

    url = reverse("product-scrape", kwargs={"parser_type": "bs4"})
    resp = api_client.post(
        url,
        data={"url": "https://example.com/broken"},
        format="json",
    )
    assert resp.status_code == 400
    assert "Parser failed" in resp.data["detail"]


@pytest.mark.django_db
def test_swagger_ui_available(api_client):
    url = reverse("schema-swagger-ui")
    resp = api_client.get(url)
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert '<div id="swagger-ui"></div>' in body


@pytest.mark.django_db
def test_redoc_available(api_client):
    url = reverse("schema-redoc")
    resp = api_client.get(url)
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert 'redoc.min.js' in body


@pytest.mark.django_db
def test_schema_json_available(api_client):
    url = reverse("schema-json", kwargs={"format": ".json"})
    resp = api_client.get(url)
    assert resp.status_code == 200
    assert resp.data["info"]["title"] == "TestPrj API"

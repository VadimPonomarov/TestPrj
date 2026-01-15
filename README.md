# Brain Product Parser – Backend Service

This Django project scrapes product data from **brain.com.ua**, stores the
normalized payload in PostgreSQL, and exposes a REST API for listing products
and exporting them to CSV.

## Prerequisites

- Docker & Docker Compose
- Python 3.11 with Poetry
- Access to the target product URLs on brain.com.ua

## Quick start

1. Install Python dependencies:

   ```bash
   poetry install
   ```

2. Start PostgreSQL via Docker Compose:

   ```bash
   docker-compose up -d db
   ```

3. Apply migrations (defaults are defined in `.env`):

   ```bash
   poetry run python manage.py migrate
   ```

4. Scrape and persist a product (direct shell example):

   ```bash
   poetry run python manage.py shell -c "from parser_app.services.brain_parser import BrainProductParser; from parser_app.models import Product; url='https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_15_Pro_Max_512GB_White_Titanium-p1044402.html'; data=BrainProductParser(url).parse(); code=data.pop('product_code'); Product.objects.update_or_create(product_code=code, defaults=data)"
   ```

5. Run the API locally:

   ```bash
   poetry run python manage.py runserver 0.0.0.0:8000
   ```

## API endpoints

Base path: `/api/`

| Method | Path                      | Description                           |
| ------ | ------------------------- | ------------------------------------- |
| POST   | `/products/scrape/`       | Scrape a Brain product and upsert it  |
| GET    | `/products/`              | Paginated product list                |
| POST   | `/products/`              | Create a product manually             |
| GET    | `/products/<id>/`         | Retrieve a product                    |
| GET    | `/products/export-csv/`   | Download all products as CSV          |

### CSV export

The CSV mirrors serializer fields. JSON structures (`images`, `metadata`,
`characteristics`) are stringified. Example:

```bash
curl -H "Host: localhost" http://127.0.0.1:8000/api/products/export-csv/ -o temp/products.csv
```

## Direct parser usage

```python
from parser_app.services.brain_parser import BrainProductParser, format_product_output

parser = BrainProductParser("https://brain.com.ua/ukr/product-url.html")
data = parser.parse()

print(format_product_output(data))
```

The parser returns a dictionary containing:
- `name`, `product_code`, `price`, `sale_price`
- `manufacturer`, `color`, `storage`
- `review_count`, `screen_diagonal`, `display_resolution`
- `images` (list of URLs)
- `characteristics` (dict)
- `metadata` (original JSON-LD details)

See `parser_app/README.md` for a deeper explanation of the parsing workflow.

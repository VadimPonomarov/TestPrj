# Brain.com.ua Product Parser

The `parser_app.services.brain_parser.BrainProductParser` class extracts rich
product data from Brain.com.ua product pages and returns it as a structured
Python dictionary.

## How it works

1. **Download** – Fetches the target page via `requests` with a desktop
   User-Agent and configurable timeout.
2. **Parse** – Loads the HTML into BeautifulSoup and locates JSON-LD payloads
   that describe a `Product` resource.
3. **Normalise offers** – Harmonises price, sale price, currency and
   availability fields from the JSON-LD `offers` block.
4. **Collect characteristics** – Searches both the DOM and inline JSON data for
   detailed attributes (colour, storage, screen size, resolution, etc.), falling
   back to parsing the product name when explicit fields are unavailable.
5. **Assemble output** – Returns a dictionary with base metadata, pricing,
   review counts, imagery, characteristics and raw metadata. If any step fails,
   an empty dictionary is returned instead of raising an exception.

## API workflow

The parser is exposed via the REST API defined in `parser_app.views`.

### 1. Scrape a Brain.com.ua product

`POST /api/products/scrape/`

Request body:

```json
{
  "url": "https://brain.com.ua/ua/product-page-url"
}
```

On success, the endpoint either creates or updates a `Product` record and
returns the normalised payload. Typical response:

```json
{
  "id": 42,
  "name": "Apple iPhone 15 Pro 256GB",
  "product_code": "MRRN3RX/A",
  "source_url": "https://brain.com.ua/...",
  "price": "44999.00",
  "metadata": {
    "sku": "123456",
    "offers": { "availability": "https://schema.org/InStock" }
  },
  "characteristics": {
    "Колір": "Natural Titanium",
    "Діагональ екрана": "6.1"
  },
  "created_at": "2026-01-15T20:47:13.120291Z",
  "updated_at": "2026-01-15T20:47:13.120291Z"
}
```

### 2. List stored products

`GET /api/products/` — returns a paginated DRF list of products ordered by
`created_at` (newest first).

`POST /api/products/` — create a product manually using the serializer schema.

### 3. Retrieve a single product

`GET /api/products/<id>/` — fetch a product by primary key.

### 4. Export products to CSV

`GET /api/products/export-csv/` — streams a CSV file with all stored products.

The CSV columns mirror the API fields; complex structures (`characteristics`,
`metadata`, `images`) are JSON-encoded inside the cells.

### Direct parser usage

For batch jobs or scripts you can call the parser service directly:

```python
from parser_app.services.brain_parser import BrainProductParser, format_product_output

parser = BrainProductParser("https://brain.com.ua/product-page-url")
product_data = parser.parse()

print(format_product_output(product_data))
```

Pass cached HTML via the `html` parameter to avoid an HTTP request. The helper
`format_product_output` renders a console-friendly summary of the parsed
content.

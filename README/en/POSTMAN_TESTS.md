# Postman tests (API validation)

This guide explains how to validate the API via Postman using environment variables and test scripts.

## Preconditions

- API is running locally:
  - Swagger: `http://localhost:8000/api/doc/`
  - Base API: `http://localhost:8000/api/`
- Database is available (Docker compose or local PostgreSQL).

## Environment variables

Use the ready-made files under `postman/`:

- `postman/TestPrj_Local.postman_environment.json`
- `postman/TestPrj_API.postman_collection.json`

Import them in Postman (File → Import → Upload Files). The environment already contains:

- `base_url` – `http://localhost:8000/api`
- `bs4_url` – a sample product URL
- `bs4_url_2` – a second sample product URL
- `search_query` – `Apple iPhone 15 128GB Black`
- `search_query_2` – a second search query
- `product_id` – pre-created but empty (tests will fill it)
- `product_id_2` – secondary id slot used by selenium flow
- `product_code`, `manufacturer`, `price_1`, `price_2` – populated from scrape responses
- `invalid_url` – invalid URL value for negative tests

## Requests covered by the collection

The collection (`TestPrj API`) contains the following groups:

### 00) Init

- Initializes deterministic run variables (generates `run_id`, `manual_code_*`, `manual_name_*`).

### 01) CRUD (manual deterministic)

- Creates 2 products via `POST /products/` with predictable `product_code` and `price`.
- Verifies:
  - listing with `product_code__icontains={{run_id}}`
  - ordering by `price`
  - filtering via `min_price`
  - pagination envelope and `page_size` behaviour

This part is intentionally independent from scrapers to keep filter/sort tests stable.

### 02) Scrape (parsers)

- `POST /products/scrape/bs4/` (twice: expects `201` then `200` with stable id)
- `POST /products/scrape/selenium/`
- `POST /products/scrape/playwright/`

### 03) Export

- `GET /products/export-csv/` with filters and ordering, verifies:
  - Content-Type is CSV
  - output contains previously created manual codes
  - ordering is applied

### 99) Negative cases

- Missing/invalid payloads for scrape endpoints (expects `400`).

## Running the collection

### Postman UI

- Select the environment (`TestPrj Local`)
- Click **Run collection**
- Run sequentially (recommended)

### Newman (CLI)

```bash
npm install -g newman
newman run postman/TestPrj_API.postman_collection.json \
  -e postman/TestPrj_Local.postman_environment.json
```

## Notes

- Selenium/Playwright scraping depends on installed browser/drivers on the machine that runs the API.
- Export endpoint supports the same filters/orderings as the list endpoint.

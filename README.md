# Brain Product Parser – Backend Service

> Django + DRF stack that scrapes **brain.com.ua** product pages, normalises the
> payload into PostgreSQL and exposes a documented REST API (Swagger & ReDoc) for
> CRUD, scraping orchestration and CSV export.

---

## Table of contents

1. [Architecture overview](#architecture-overview)
2. [Tech stack](#tech-stack)
3. [Repository layout](#repository-layout)
4. [Cloning & local setup](#cloning--local-setup)
5. [Running with Docker Compose](#running-with-docker-compose)
6. [Environment configuration](#environment-configuration)
7. [Database & static assets](#database--static-assets)
8. [Accessing the API & Swagger UI](#accessing-the-api--swagger-ui)
9. [Working with the API](#working-with-the-api)
10. [Direct parser usage](#direct-parser-usage)
11. [Testing & quality gates](#testing--quality-gates)
12. [Troubleshooting](#troubleshooting)

---

## Architecture overview

```
┌────────────┐    HTTP/JSON     ┌──────────────┐
│ Swagger UI │ ───────────────► │ Django + DRF │
└────┬───────┘                  │ (parser_app) │
     │                          └────┬─────────┘
     │ scrape request (parser_type) │
     │                              ▼
     │                      ┌──────────────┐
     │                      │ Parser layer │◄─────────┐
     │                      │ (BS4 / Sel / │          │
     │                      │  Playwright) │          │
     │                      └────┬─────────┘          │
     │                           │ ProductData        │
     │                           ▼                    │
     │                    ┌──────────────┐            │
     └────────────────────│ PostgreSQL   │◄───────────┘
                          └──────────────┘
```

- **parser_app** – domain module with serializers, views, filters and parser
  factory (`parser_app/services/factory.py`).
- **Parsers** – BeautifulSoup (default), Selenium and Playwright adapters reuse
  `BrainProductParser` for HTML parsing of brain.com.ua pages.
- **API layer** – DRF viewset-style endpoints for listing products, scraping,
  exporting to CSV, etc.
- **Docs** – `drf-yasg` generates Swagger UI (`/api/doc/`) and ReDoc
  (`/api/redoc/`) behind the `config.docs` app.
- **Docker** – `docker-compose.yml` wires PostgreSQL, Django app and optional
  Nginx front proxy. The `web` service auto waits for DB, applies migrations,
  collects static files and launches Gunicorn-ready dev server.

## Tech stack

- Python 3.11, Django 5, Django REST Framework
- PostgreSQL 14
- Docker & Docker Compose
- Parsing libs: BeautifulSoup, optional Selenium & Playwright
- Tooling: pytest, pytest-django, drf-yasg, Django Filters, pandas (CSV export)

## Repository layout

```
config/                # Django project settings + docs URLs
parser_app/            # Domain app (models, serializers, parsers, tests)
parser_app/parsers/    # Parser implementations (bs4/selenium/playwright)
parser_app/services/   # Legacy parser utilities & factory
parser_app/tests/      # API integration tests (pytest + DRF client)
nginx/                 # Reverse-proxy configuration (optional)
docker-compose.yml     # DB + web + nginx stack
pytest.ini             # Pytest configuration
```

## Cloning & local setup

```bash
git clone https://github.com/VadimPonomarov/TestPrj.git
cd TestPrj
cp .env.example .env        # adjust DB credentials, secrets, etc.
poetry install              # or pip install -r requirements.txt if preferred
poetry run python manage.py migrate
poetry run python manage.py runserver 0.0.0.0:8000
```

**Helpful commands**

- `poetry run python manage.py createsuperuser`
- `poetry run python manage.py collectstatic`
- `poetry run python manage.py wait_db --timeout=60 --interval=1`

## Running with Docker Compose

Prerequisites: Docker ≥ 24, Compose v2, `.env` configured.

```bash
git clone https://github.com/VadimPonomarov/TestPrj.git
cd TestPrj
cp .env.example .env
docker compose up --build
```

Services:

| Service | Port | Description |
| ------- | ---- | ----------- |
| `db`    | 5433 | PostgreSQL 14 with health check |
| `web`   | 8000 | Django app (autoreloads in dev) |
| `nginx` | 80   | Optional reverse proxy exposing static/media and forwarding to `web` |

Logs stream in the same terminal. First boot performs DB migrations and collects static files automatically.

> Stop stack: `docker compose down -v` (add `-v` to drop postgres volume).

## Environment configuration

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `DJANGO_SETTINGS_MODULE` | Django settings module | `config.settings` |
| `DATABASE_URL` / `POSTGRES_*` | DB credentials | see `.env.example` |
| `SWAGGER_DEFAULT_API_URL` | Base URL shown in Swagger | `http://localhost` |
| `IS_DOCKER` | Enables Docker-specific tweaks (e.g., wait_db) | `false` |
| `TEMP_DIR` | Directory for CSV exports | `temp/` |

Update `.env` or Docker Compose overrides to match your environment (Playwright requires Chromium dependencies if you enable that parser).

## Database & static assets

```bash
poetry run python manage.py migrate
poetry run python manage.py collectstatic
poetry run python manage.py createsuperuser
```

In Docker these steps are executed automatically by the `web` entry command. To reset local DB:

```bash
docker compose down -v
docker compose up
```

## Accessing the API & Swagger UI

- Swagger UI: `http://localhost:8000/api/doc/`
- ReDoc: `http://localhost:8000/api/redoc/`
- Raw schema: `http://localhost:8000/api/doc.json`

Root `/` redirects to Swagger UI by default (see `config/urls.py`).

## Working with the API

Base prefix: `/api/`

| Method | Path | Description |
| ------ | ---- | ----------- |
| POST | `/products/` | Create product manually |
| GET | `/products/` | List + filter + paginate products (`search`, `min_price`, `ordering`, etc.) |
| GET | `/products/<id>/` | Retrieve product detail |
| GET | `/products/export-csv/` | Stream CSV of all products |
| POST | `/products/scrape/<parser_type>/` | Trigger scraper (`bs4`, `selenium`, `playwright`) |

**Scrape request payload**

```json
{
  "url": "https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_16_Pro_Max_256GB_Black_Titanium-p1145443.html"
}
```

- `url` **or** `query` must be provided. `ProductScrapeRequestSerializer` auto
  fills sensible defaults depending on `parser_type`.
- Successful scraping either creates or updates a `Product` record and returns
  the serialised instance.

**Curl examples**

```bash
# Scrape via default BeautifulSoup parser
curl -X POST http://localhost:8000/api/products/scrape/bs4/ \
     -H "Content-Type: application/json" \
     -d '{"url":"https://brain.com.ua/ukr/..."}'

# List with filters & ordering
curl "http://localhost:8000/api/products/?search=iphone&ordering=-price&page_size=20"

# Export CSV
curl -o products.csv http://localhost:8000/api/products/export-csv/
```

## Direct parser usage

```python
from parser_app.services.parsers.brain.parser import BrainProductParser
from parser_app.services.parsers.brain.parser import format_product_output

parser = BrainProductParser(
    "https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_15_Pro_Max_512GB_White_Titanium-p1044402.html"
)
payload = parser.parse()
print(format_product_output(payload))
```

Returned fields include:

- `name`, `product_code`, price info
- `manufacturer`, `color`, `storage`
- `review_count`, `screen_diagonal`, `display_resolution`
- `images`, `characteristics`, `metadata`

## Testing & quality gates

```bash
poetry run pytest
poetry run pytest parser_app/tests/test_endpoints.py -k scrape
```

Fixtures use DRF `APIClient` and hit real endpoints, so ensure DB/migrations are ready. For coverage add `--cov=parser_app`.

## Troubleshooting

| Symptom | Fix |
| ------- | ---- |
| `django.db.utils.OperationalError: could not connect to server` | Ensure Postgres is running (`docker compose ps`). Increase `wait_db` timeout if needed. |
| Swagger served over wrong host | Set `SWAGGER_DEFAULT_API_URL` or access via Nginx (`http://localhost`). |
| Playwright parser errors about missing browsers | Inside the container run `playwright install --with-deps chromium` or rely on BS4/Selenium parsers. |
| Static files 404 when using Nginx | Re-run `python manage.py collectstatic` and verify `static_volume` is mounted. |

---

Need more? Reach out via the contact in Swagger metadata or open an issue on GitHub.

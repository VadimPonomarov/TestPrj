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

- Python 3.12, Django 5, Django REST Framework
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

### Option A (recommended): local run without Docker (`deploy.local.py`)

Prerequisites:

- Python 3.12+
- Poetry
- PostgreSQL running locally (default: `127.0.0.1:5432`) or Docker DB on `127.0.0.1:5434`

```powershell
git clone https://github.com/VadimPonomarov/TestPrj.git
Set-Location TestPrj
python deploy.local.py
```

### Option B: manual local run

```powershell
# create/edit .env.local (local environment)
# minimal required keys: DEBUG, SECRET_KEY, DJANGO_ALLOWED_HOSTS, SQL_*
poetry install
poetry run python manage.py wait_db --timeout=60 --interval=1
poetry run python manage.py migrate
poetry run python manage.py collectstatic --noinput --clear
poetry run python manage.py runserver 127.0.0.1:8000
```

See **`DEPLOYMENT.md`** for a full local/no-Docker walkthrough (including using Docker DB with local Django).

**Helpful commands**

- `poetry run python manage.py createsuperuser`
- `poetry run python manage.py collectstatic`
- `poetry run python manage.py wait_db --timeout=60 --interval=1`

## Running with Docker Compose

Prerequisites: Docker ≥ 24, Compose v2, `.env.docker` configured.

```powershell
git clone https://github.com/VadimPonomarov/TestPrj.git
Set-Location TestPrj
# edit .env.docker if you need custom credentials
docker compose up --build
```

Services:

| Service | Port | Description |
| ------- | ---- | ----------- |
| `db`    | 5434 | PostgreSQL 14 with health check |
| `web`   | 8000 | Django app (autoreloads in dev) |
| `nginx` | 80   | Optional reverse proxy exposing static/media and forwarding to `web` |

Logs stream in the same terminal. First boot performs DB migrations and collects static files automatically.

> Stop stack: `docker compose down -v` (add `-v` to drop postgres volume).

## Deployment guide

Detailed instructions (including `deploy.py` usage, classic Docker workflow, db-only mode, troubleshooting) live in **`DEPLOYMENT.md`**. Open that file after cloning to follow the recommended flow.

## Local Scrapy-only workflow (no web container)

Sometimes you only need the PostgreSQL service while keeping Scrapy spiders running locally (outside Docker). Steps:

1. Start only the DB container:
   ```powershell
   docker compose up db -d
   ```
2. Set temporary environment overrides (or rely on `.env.local`) so local Scrapy talks to the container:
   ```powershell
   $env:SQL_HOST = "127.0.0.1"
   $env:SQL_PORT = "5434"
   $env:SQL_DATABASE = "mydb"
   $env:SQL_USER = "myuser"
   $env:SQL_PASSWORD = "mypassword"
   $env:DJANGO_SETTINGS_MODULE = "config.settings"
   ```
3. Activate Poetry shell (or prefix with `poetry run`) and launch spiders from `scrapy_project`:
   ```powershell
   Set-Location scrapy_project
   poetry run scrapy crawl brain_bs4 -a "urls=https://brain.com.ua/..."
   ```

Only PostgreSQL runs in Docker; Django/DRF stays idle. The spiders still reuse the same serializers/models, so the API (if/when you start it) immediately sees the new data.

## Environment configuration

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `DJANGO_SETTINGS_MODULE` | Django settings module | `config.settings` |
| `SQL_*` / `POSTGRES_*` | DB credentials | see `.env.docker` (Docker) or `.env.local` (local) |
| `SWAGGER_DEFAULT_API_URL` | Base URL shown in Swagger | `http://localhost` |
| `IS_DOCKER` | Enables Docker-specific tweaks (e.g., wait_db) | `false` |
| `TEMP_DIR` | Directory for CSV exports | `temp/` |

Update `.env.docker` (Docker) or `.env.local` (local) to match your environment (Playwright requires Chromium dependencies if you enable that parser).

## Database & static assets

```powershell
poetry run python manage.py migrate
poetry run python manage.py collectstatic
poetry run python manage.py createsuperuser
```

In Docker these steps are executed automatically by the `web` entry command. To reset local DB:

```powershell
docker compose down -v
docker compose up
```

## Accessing the API & Swagger UI

- Direct (web):
  - Swagger UI: `http://localhost:8000/api/doc/`
  - ReDoc: `http://localhost:8000/api/redoc/`
  - Raw schema: `http://localhost:8000/api/doc.json`
- Via Nginx (if enabled):
  - Swagger UI: `http://localhost/api/doc/`
  - ReDoc: `http://localhost/api/redoc/`

Root `/` redirects to Swagger UI by default (see `config/urls.py`).

## Working with the API

Base prefix: `/api/`

| Method | Path | Description |
| ------ | ---- | ----------- |
| POST | `/products/` | Create product manually |
| GET | `/products/` | List + filter + paginate products (`search`, `min_price`, `ordering`, etc.) |
| GET | `/products/<id>/` | Retrieve product detail |
| GET | `/products/export-csv/` | Export CSV (supports the same filters and ordering as listing) |
| POST | `/products/scrape/bs4/` | Trigger scraper via BeautifulSoup |
| POST | `/products/scrape/selenium/` | Trigger scraper via Selenium |
| POST | `/products/scrape/playwright/` | Trigger scraper via Playwright |

**Scrape request payload**

- **/products/scrape/bs4/**: `url` is required, `query` is forbidden.
- **/products/scrape/selenium/** and **/products/scrape/playwright/**: `query` is required (site search workflow).

Examples:

```json
{
  "url": "https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_16_Pro_Max_256GB_Black_Titanium-p1145443.html"
}
```

```json
{
  "query": "Apple iPhone 15 128GB Black"
}
```
- Successful scraping either creates or updates a `Product` record and returns
  the serialised instance.

**Curl examples**

```powershell
# Scrape via default BeautifulSoup parser
$body = '{"url":"https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_16_Pro_Max_256GB_Black_Titanium-p1145443.html"}'
Invoke-RestMethod -Method Post `
    -Uri "http://localhost:8000/api/products/scrape/bs4/" `
    -ContentType "application/json" `
    -Body $body

# Scrape via Selenium/Playwright parsers (search-driven)
$body = '{"query":"Apple iPhone 15 128GB Black"}'
Invoke-RestMethod -Method Post `
    -Uri "http://localhost:8000/api/products/scrape/selenium/" `
    -ContentType "application/json" `
    -Body $body

# List with filters & ordering
Invoke-RestMethod -Uri "http://localhost:8000/api/products/?search=iphone&ordering=-price&page_size=20" |
    ConvertTo-Json -Depth 4

# Export CSV
Invoke-WebRequest -Uri "http://localhost:8000/api/products/export-csv/" -OutFile "products.csv"
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

```powershell
poetry run pytest
poetry run pytest parser_app/tests/test_endpoints.py -k scrape
```

## Scrapy integration

The `scrapy_project/` folder contains Scrapy spiders that mirror the API scraping behaviour
and persist results to the same database.

- Default feed export: `outputs/%(name)s_%(time)s.csv` (can be overridden via `SCRAPY_FEED_URI`).

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

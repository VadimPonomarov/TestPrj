# Scrapy integration for Brain Parser

This folder contains a Scrapy project that reuses existing parsers
(`parser_app.parsers.*`) and DRF serializers/models to persist data into the same
PostgreSQL database that the API uses.

## Prerequisites

1. Python 3.12+ and Poetry (or pip) installed.
2. Backend dependencies installed: `poetry install`.
3. Environment variables configured (`DJANGO_SETTINGS_MODULE`, `SQL_*`) via `.env.local` (local) or `.env.docker` (Docker).
4. PostgreSQL is running (locally or via `docker compose up db web`).
5. Optional: browser dependencies installed for Selenium/Playwright parsers.

## Local development setup

If you want to run Scrapy spiders locally, install Scrapy-related dependencies.

Recommended (verified): install dev dependencies (Scrapy is in the `dev` group):

```bash
poetry install --with dev

# Playwright initialization (if needed)
playwright install
playwright install-deps
```

> These dependencies affect only your local environment. They do not change Docker containers.

### `.env.docker` vs `.env.local`

`.env.docker` is intended for containers (usually `SQL_HOST=db`, `SQL_PORT=5432`).
For local Scrapy runs use `.env.local` (loaded automatically by the project):

```ini
SQL_HOST=127.0.0.1
SQL_PORT=5434
SQL_DATABASE=mydb
SQL_USER=myuser
SQL_PASSWORD=mypassword
```

This way Docker uses `.env.docker`, while local Scrapy uses `.env.local` without manual PowerShell overrides.

## Structure

```text
scrapy_project/
├── scrapy.cfg
├── brain_scraper/
│   ├── django_setup.py
│   ├── items.py
│   ├── pipelines.py
│   ├── settings.py
│   ├── utils.py
│   └── spiders/
│       ├── base.py
│       ├── bs4_spider.py
│       ├── selenium_spider.py
│       └── playwright_spider.py
```

## Run examples

### 1) Fill the DB

```powershell
Set-Location scrapy_project
$env:DJANGO_SETTINGS_MODULE = "config.settings"
scrapy crawl brain_bs4 -a "urls=https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_16_Pro_Max_256GB_Black_Titanium-p1145443.html"
```

Other spiders:

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings"
scrapy crawl brain_selenium -a "query=Apple iPhone 15 128GB Black"

$env:DJANGO_SETTINGS_MODULE = "config.settings"
scrapy crawl brain_playwright -a "query=Apple iPhone 15 128GB Black"
```

> Selenium/Playwright require installed browsers/drivers.

### 2) Save output to a file (JSON/CSV)

Example JSON:

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings"
$env:SCRAPY_FEED_URI = "outputs/bs4.json"
$env:SCRAPY_FEED_FORMAT = "json"
scrapy crawl brain_bs4
```

Example CSV:

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings"
$env:SCRAPY_FEED_URI = "outputs/bs4.csv"
$env:SCRAPY_FEED_FORMAT = "csv"
scrapy crawl brain_bs4
```

### 3) Verify via API

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/products/?ordering=-created_at" | ConvertTo-Json -Depth 4
Invoke-WebRequest -Uri "http://localhost:8000/api/products/export-csv/" -OutFile "temp/products.csv"
```

## Testing

1. Ensure Python deps are installed: `poetry install`.
2. Run `poetry run pytest parser_app/tests -k scrape`.
3. For manual smoke test (verified):
   - Ensure DB is up (Docker): `docker compose up -d db`
   - Ensure Django can connect: `poetry run python manage.py wait_db --timeout=30 --interval=1`
   - Apply migrations: `poetry run python manage.py migrate --noinput`
   - Run spider via Poetry:
     ```powershell
     Set-Location scrapy_project
     poetry run scrapy crawl brain_bs4 -a "urls=https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_16_Pro_Max_256GB_Black_Titanium-p1145443.html"
     ```
   - Verify data persisted (example):
     ```powershell
     poetry run python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); import django; django.setup(); from parser_app.models import Product; print(Product.objects.count())"
     ```

## Common issues

| Symptom                                      | Fix                                                                                                   |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `ModuleNotFoundError: django` during `scrapy crawl` | Use `poetry run scrapy ...` or activate the venv where Django is installed.                            |
| Playwright / Selenium errors                  | Install drivers/browsers: `playwright install --with-deps chromium`, `pip install selenium` + chromedriver. |
| Data is not persisted                         | Check pipeline logs (`Persisted product ...`). Errors will appear in Scrapy/DRF logs.                 |
| DB is empty after Scrapy run                  | Ensure Scrapy and API point to the same DB connection settings (`SQL_*`).                              |
| Issues copying commands in PowerShell         | Prefer clean single-line commands (avoid `\`) or use PowerShell continuation `` ` ``.                |

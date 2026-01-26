# Run Scrapy spiders

All examples assume you are in the repository root:

- `D:/myDocuments/studying/Projects/TestPrj`

## 1) Run via Django management command (recommended)

List available spiders:

```powershell
D:\myDocuments\studying\Projects\TestPrj\.venv\Scripts\python.exe manage.py run_spider any --list
```

Run `brain_bs4` (URLs are comma-separated):

```powershell
D:\myDocuments\studying\Projects\TestPrj\.venv\Scripts\python.exe manage.py run_spider brain_bs4 -a urls="https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_15_128GB_Black-p1044347.html"
```

Run `brain_selenium`:

```powershell
D:\myDocuments\studying\Projects\TestPrj\.venv\Scripts\python.exe manage.py run_spider brain_selenium -a query="Apple iPhone 15 128GB Black"
```

Run `brain_playwright`:

```powershell
D:\myDocuments\studying\Projects\TestPrj\.venv\Scripts\python.exe manage.py run_spider brain_playwright -a query="Apple iPhone 15 128GB Black"
```

Disable DB persistence (smoke runs):

```powershell
$env:SCRAPY_DISABLE_DB_PIPELINE = "1"
```

Notes:

- `-a/--arg` supports multiple values:

```powershell
D:\myDocuments\studying\Projects\TestPrj\.venv\Scripts\python.exe manage.py run_spider brain_bs4 -a urls="url1,url2,url3"
```

- Timing output for spiders is provided by `brain_scraper.extensions.SpiderTimingExtension`.

## 2) Run via Scrapy CLI

Set Django env vars and run from `scrapy_project` directory.

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings"
$env:PYTHONPATH = (Resolve-Path ".").Path
Push-Location ".\scrapy_project"

# list
poetry run scrapy list

# run
poetry run scrapy crawl brain_bs4 -a urls="https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_15_128GB_Black-p1044347.html"

Pop-Location
```

Save output to file:

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings"
$env:PYTHONPATH = (Resolve-Path ".").Path
$env:SCRAPY_DISABLE_DB_PIPELINE = "1"
Push-Location ".\scrapy_project"

poetry run scrapy crawl brain_playwright -a query="Apple iPhone 15 128GB Black" -O "outputs/playwright.json" -s CLOSESPIDER_ITEMCOUNT=1 -s CLOSESPIDER_TIMEOUT=180

Pop-Location
```

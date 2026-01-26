# Запуск павуків Scrapy

> **Працюємо з PowerShell.** Перед запуском переконайтесь, що знаходитеся в корені репозиторію `D:/myDocuments/studying/Projects/TestPrj`.

## Швидкий старт: команди (копіюй та запускай)

> **Передумови успіху** (як підготувати середовище):
>
> 1. **Підняти PostgreSQL.**
>    - Якщо використовуємо Docker: `docker compose up -d db` (з файлу `docker-compose.yml`), після чого перевіряємо здоровʼя сервісу `db`.
>    - Якщо локальний інстанс: створити базу/користувача згідно з `.env.local` (типово `host=127.0.0.1`, `port=5434`, `user=myuser`). Можна скористатися підказками з `deploy.local.py` (`poetry run python deploy.local.py --skip-install --no-runserver`).
>    - Для перевірки доступності виконай `poetry run python manage.py wait_db --timeout=60`.
> 2. **Підготувати Python оточення.**
>    - Активуй віртуальне середовище: `D:\myDocuments\studying\Projects\TestPrj\.venv\Scripts\Activate.ps1` (якщо створене Poetry).
>    - Встанови залежності (один раз): `poetry install` у корені репозиторію.
> 3. **Налаштувати змінні оточення.**
>    - Для команд PowerShell: 
>      ```powershell
>      $env:DJANGO_SETTINGS_MODULE = "config.settings"
>      $env:PYTHONPATH = (Resolve-Path ".").Path
>      ```
>    - Переконайся, що `.env.local` існує та містить правильні креденшали до БД (скрипт `deploy.local.py` створить його за потреби).
>
> 4. **Автономні скрипти (без `manage.py`).**
>    - Ініціалізуй Django через `modules/load_django.py` перед використанням ORM чи пайплайнів:
>
      ```python
      from modules.load_django import setup_django
      setup_django()
      ```
>    - Запускай standalone-скрипти через Poetry (використовує `pyproject.toml`):
>
      ```powershell
      poetry run python modules\brain_bs4_parser.py "https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_15_128GB_Black-p1044347.html"
      poetry run python modules\brain_selenium_parser.py --query "Apple iPhone 15 128GB Black"
      poetry run python modules\brain_playwright_parser.py --query "Apple iPhone 15 128GB Black"
      ```
>
>    - Якщо Poetry недоступний, можна запускати напряму через інтерпретатор з `.venv`:
>
      ```powershell
      D:\myDocuments\studying\Projects\TestPrj\.venv\Scripts\python.exe modules\brain_bs4_parser.py "https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_15_128GB_Black-p1044347.html"
      ```
>    - У цьому випадку активуй `.venv` (`.venv\Scripts\Activate.ps1`) або встанови залежності глобально перед запуском.
>
> **Запуск команд прямо з цього файлу.**
>
> Можна запустити `powershell`-блоки з цього `.md` через runner `modules/run_md.py`:
> 
> ```powershell
> # dry-run (покаже блоки, але не виконає)
> poetry run python modules\run_md.py scrapy_project\RUN_SPIDERS.md
>
> # реально виконати
> poetry run python modules\run_md.py scrapy_project\RUN_SPIDERS.md --run
> ```
>
> Якщо Poetry недоступний, можна використати глобальний інтерпретатор (за умови встановлених залежностей):
>
> ```powershell
> python modules\run_md.py scrapy_project\RUN_SPIDERS.md --run
> ```
>

### Django management command (рекомендовано)

- Показати всіх доступних павуків:

  ```powershell
  D:\myDocuments\studying\Projects\TestPrj\.venv\Scripts\python.exe manage.py run_spider brain_bs4 --list
  ```

- Запустити `brain_bs4` (URL-и через кому):

  ```powershell
  D:\myDocuments\studying\Projects\TestPrj\.venv\Scripts\python.exe manage.py run_spider brain_bs4 -a urls="https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_15_128GB_Black-p1044347.html"
  ```

- Запустити `brain_selenium` (пошуковий запит):

  ```powershell
  D:\myDocuments\studying\Projects\TestPrj\.venv\Scripts\python.exe manage.py run_spider brain_selenium -a query="Apple iPhone 15 128GB Black"
  ```

- Запустити `brain_playwright` (пошуковий запит):

  ```powershell
  D:\myDocuments\studying\Projects\TestPrj\.venv\Scripts\python.exe manage.py run_spider brain_playwright -a query="Apple iPhone 15 128GB Black"
  ```

- Тимчасово вимкнути запис у БД (smoke-ран):

  ```powershell
  $env:SCRAPY_DISABLE_DB_PIPELINE = "1"
  ```

### Scrapy CLI

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings"
$env:SCRAPY_SETTINGS_MODULE = "brain_scraper.settings"
$env:PYTHONPATH = (Resolve-Path ".").Path + ";" + (Resolve-Path ".\scrapy_project").Path

# показати список павуків
poetry run scrapy list

# запустити brain_bs4
poetry run scrapy crawl brain_bs4 -a urls="https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_15_128GB_Black-p1044347.html"
```

### Scrapy CLI + збереження результату у файл

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings"
$env:SCRAPY_SETTINGS_MODULE = "brain_scraper.settings"
$env:PYTHONPATH = (Resolve-Path ".").Path + ";" + (Resolve-Path ".\scrapy_project").Path
$env:SCRAPY_DISABLE_DB_PIPELINE = "1"

poetry run scrapy crawl brain_playwright -a query="Apple iPhone 15 128GB Black" -O "scrapy_project/outputs/playwright.json" -s CLOSESPIDER_ITEMCOUNT=1 -s CLOSESPIDER_TIMEOUT=180
```

---

## Деталі та додаткові поради

- Аргументи `-a/--arg` підтримують кілька значень через кому:

  ```powershell
  D:\myDocuments\studying\Projects\TestPrj\.venv\Scripts\python.exe manage.py run_spider brain_bs4 -a urls="https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_15_128GB_Black-p1044347.html,https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_16_Pro_Max_256GB_Black_Titanium-p1145443.html"
  ```

- Вивантаження з БД у CSV (DRF API):

  ```powershell
  D:\myDocuments\studying\Projects\TestPrj\.venv\Scripts\python.exe manage.py runserver
  ```

  ```powershell
  $out = "temp\assignment\outputs\products.csv"
  New-Item -ItemType Directory -Force (Split-Path $out) | Out-Null
  Invoke-WebRequest "http://127.0.0.1:8000/api/products/export-csv/" -OutFile $out
  ```

- За вимірювання часу виконання відповідає розширення `brain_scraper.extensions.SpiderTimingExtension`.

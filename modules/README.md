# Standalone-парсеры (`modules/`)

В папке `modules/` лежат standalone-скрипты для парсинга Brain.com.ua.

## Скрипты

- `brain_bs4_parser.py` — requests + lxml (без браузера)
- `brain_selenium_parser.py` — Selenium (headless Chrome)
- `brain_playwright_parser.py` — Playwright (headless Chromium)

## Быстрый запуск

Все команды ниже запускай из корня репозитория.

PowerShell:

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings"
$env:PYTHONPATH = (Resolve-Path ".").Path
```

BS4 (URL напрямую):

```powershell
poetry run python modules\brain_bs4_parser.py "https://brain.com.ua/ukr/...-pXXXXXX.html"
```

или:

```powershell
poetry run python modules\brain_bs4_parser.py --url "https://brain.com.ua/ukr/...-pXXXXXX.html"
```

Selenium:

- Прямой URL товара:

```powershell
poetry run python modules\brain_selenium_parser.py "https://brain.com.ua/ukr/...-pXXXXXX.html"
```

- Workflow через поиск:

```powershell
poetry run python modules\brain_selenium_parser.py --query "Apple iPhone 15 128GB Black"
```

Playwright:

- Прямой URL товара:

```powershell
poetry run python modules\brain_playwright_parser.py "https://brain.com.ua/ukr/...-pXXXXXX.html"
```

- Workflow через поиск:

```powershell
poetry run python modules\brain_playwright_parser.py --query "Apple iPhone 15 128GB Black"
```

## Вывод

- В консоль печатается словарь полей товара.
- CSV можно указать через `--csv ...`
- Сохранение в БД включается флагом `--save-db`.

## Сохранение в БД

Флаг `--save-db` использует Django ORM и инициализацию Django через `modules/load_django.py`.

Важно:

- Должны быть корректно настроены переменные окружения БД для `config.settings`.
- Если миграции ещё не применялись — выполните:

```bash
poetry run python manage.py migrate
```

## Выгрузка из БД в CSV

Экспорт доступен через DRF endpoint `GET /api/products/export-csv/`.

```powershell
poetry run python manage.py runserver
$out = "temp\assignment\outputs\products.csv"
New-Item -ItemType Directory -Force (Split-Path $out) | Out-Null
Invoke-WebRequest "http://127.0.0.1:8000/api/products/export-csv/" -OutFile $out
```

## Инициализация Django в standalone-скриптах

Если ты пишешь свой standalone-скрипт и хочешь использовать ORM напрямую:

```python
from modules.load_django import setup_django

setup_django()
```

## Полная инструкция

См. подробный гайд:

- `README/uk/MODULES_PARSERS.md`

# Standalone-парсеры (`modules/`)

В папке `modules/` лежат standalone-скрипты для парсинга Brain.com.ua.

## Скрипты

- `brain_bs4_parser.py` — requests + lxml (без браузера)
- `brain_selenium_parser.py` — Selenium (headless Chrome)
- `brain_playwright_parser.py` — Playwright (headless Chromium)

## Быстрый запуск

BS4 (URL напрямую):

```bash
poetry run python modules/brain_bs4_parser.py --url "https://brain.com.ua/ukr/...-pXXXXXX.html"
```

Selenium (workflow через поиск):

```bash
poetry run python modules/brain_selenium_parser.py
```

Playwright (workflow через поиск):

```bash
poetry run python modules/brain_playwright_parser.py
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

## Полная инструкция

См. подробный гайд:

- `README/uk/MODULES_PARSERS.md`

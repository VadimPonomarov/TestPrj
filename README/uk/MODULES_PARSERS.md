# Запуск standalone-парсерів з папки `modules/`

Цей документ описує, як запускати standalone-скрипти з папки `modules/` (BS4 / Selenium / Playwright), як зберігати результати у CSV та у базу даних через Django ORM, а також як запускати DRF API.

## Передумови

- Використовуйте Poetry (проєкт уже налаштований під нього).
- Переконайтеся, що залежності встановлені:

```bash
poetry install
```

## 1) Запуск BS4 (requests + lxml)

Скрипт:

- `modules/brain_bs4_parser.py`

Запуск (URL напряму):

```bash
poetry run python modules/brain_bs4_parser.py "https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_16_Pro_Max_256GB_Black_Titanium-p1145443.html"
```

Збереження в CSV:

```bash
poetry run python modules/brain_bs4_parser.py "https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_16_Pro_Max_256GB_Black_Titanium-p1145443.html" --csv temp/assignment/outputs/bs4.csv
```

Збереження у БД (Django ORM):

```bash
poetry run python modules/brain_bs4_parser.py "https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_16_Pro_Max_256GB_Black_Titanium-p1145443.html" --save-db
```

## 2) Запуск Selenium (Chrome)

Скрипт:

- `modules/brain_selenium_parser.py`

Запуск:

```bash
poetry run python modules/brain_selenium_parser.py
```

Workflow через пошук:

```bash
poetry run python modules/brain_selenium_parser.py --query "Apple iPhone 15 128GB Black"
```

Збереження у CSV:

```bash
poetry run python modules/brain_selenium_parser.py --csv temp/assignment/outputs/selenium.csv
```

Збереження у БД:

```bash
poetry run python modules/brain_selenium_parser.py --save-db
```

Примітки:

- Потрібен встановлений Chrome.
- Драйвер підтягується через `webdriver_manager`.
- Скрипт працює headless.

## 3) Запуск Playwright

Скрипт:

- `modules/brain_playwright_parser.py`

Перед першим запуском Playwright, можливо, треба встановити браузери (залежить від оточення):

```bash
poetry run playwright install
```

Запуск:

```bash
poetry run python modules/brain_playwright_parser.py
```

Workflow через пошук:

```bash
poetry run python modules/brain_playwright_parser.py --query "Apple iPhone 15 128GB Black"
```

Збереження у CSV:

```bash
poetry run python modules/brain_playwright_parser.py --csv temp/assignment/outputs/playwright.csv
```

Збереження у БД:

```bash
poetry run python modules/brain_playwright_parser.py --save-db
```

## 4) Як працює збереження у БД зі standalone-скриптів

Standalone-скрипти викликають `save_product_to_db(...)` з `parser_app/common/db.py`.

Всередині використовується `modules/load_django.py`, який:

- додає корінь проєкту в `sys.path`
- виставляє `DJANGO_SETTINGS_MODULE=config.settings`
- викликає `django.setup()`

Після цього використовується ORM-модель `parser_app.models.Product` та виконується `update_or_create` за ключем `product_code`.

Важливо:

- База даних має бути доступна та налаштована у `config/settings.py` (через env або локальні налаштування).
- Якщо міграції не застосовані — виконайте їх перед збереженням:

```bash
poetry run python manage.py migrate
```

## 5) Запуск DRF API

Локально:

```bash
poetry run python manage.py migrate
poetry run python manage.py runserver
```

Основні scrape-ендпоінти:

- `POST /api/products/scrape/bs4/`
- `POST /api/products/scrape/selenium/`
- `POST /api/products/scrape/playwright/`

Експорт з БД у CSV:

- `GET /api/products/export-csv/`

Тіло запиту (URL напряму):

```json
{
  "url": "https://brain.com.ua/ukr/...-pXXXXXX.html"
}
```

Тіло запиту (workflow через пошук, для Selenium/Playwright):

```json
{
  "query": "Apple iPhone 15 128GB Black"
}
```

Приклад завантаження CSV у файл:

```bash
curl -L "http://127.0.0.1:8000/api/products/export-csv/" -o "temp/assignment/outputs/products.csv"
```

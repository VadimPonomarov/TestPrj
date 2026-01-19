# Парсер товарів Brain.com.ua

Клас `parser_app.services.parsers.brain.parser.BrainProductParser` витягує детальні
дані про товар зі сторінок Brain.com.ua та повертає їх як структурований словник
Python.

## Як це працює

1. **Завантаження** – отримує HTML сторінки через `requests` з desktop User-Agent та
   налаштовуваним timeout.
2. **Парсинг** – завантажує HTML у BeautifulSoup і знаходить JSON-LD, який описує
   ресурс `Product`.
3. **Нормалізація offers** – узгоджує ціну, акційну ціну, валюту та availability з
   JSON-LD блоку `offers`.
4. **Збір характеристик** – шукає дані у DOM та inline JSON (колір, памʼять, діагональ,
   роздільна здатність тощо), і за потреби робить fallback до розбору назви товару.
5. **Формування результату** – повертає словник з базовими метаданими, цінами,
   кількістю відгуків, зображеннями, характеристиками і raw metadata. Якщо будь-який
   крок падає, повертається порожній словник замість виключення.

## API workflow

Парсер доступний через REST API, визначений у `parser_app.views`.

### 1. Спарсити сторінку товару Brain.com.ua

Scrape-ендпоінти:

- `POST /api/products/scrape/bs4/`
- `POST /api/products/scrape/selenium/`
- `POST /api/products/scrape/playwright/`

Тіло запиту:

```json
{
  "url": "https://brain.com.ua/ua/product-page-url"
}
```

Для Selenium/Playwright використовуйте workflow на основі пошуку:

```json
{
  "query": "Apple iPhone 15 128GB Black"
}
```

У разі успіху ендпоінт створює або оновлює запис `Product` і повертає
нормалізований payload. Приклад відповіді:

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

### 2. Список збережених товарів

`GET /api/products/` — повертає пагінований список DRF, відсортований за
`created_at` (спочатку нові).

`POST /api/products/` — створює товар вручну через схему серіалізатора.

### 3. Отримати один товар

`GET /api/products/<id>/` — отримати товар за primary key.

### 4. Експорт у CSV

`GET /api/products/export-csv/` — стрімить CSV з усіма товарами.

Колонки CSV повторюють поля API; складні структури (`characteristics`, `metadata`,
`images`) JSON-кодуються всередині клітинок.

### Пряме використання парсера

Для батчових задач або скриптів можна викликати сервіс напряму:

```python
from parser_app.services.parsers import BrainProductParser, format_product_output

parser = BrainProductParser("https://brain.com.ua/product-page-url")
product_data = parser.parse()

print(format_product_output(product_data))
```

Можна передати кешований HTML через параметр `html`, щоб уникнути HTTP-запиту.
Хелпер `format_product_output` виводить дружній до консолі підсумок.

# Postman-тести (валідація API)

Цей документ описує, як перевірити API через Postman за допомогою змінних середовища та тестових скриптів.

## Передумови

- API запущений локально:
  - Swagger: `http://localhost:8000/api/doc/`
  - Base API: `http://localhost:8000/api/`
- База даних доступна (Docker compose або локальний PostgreSQL).

## Змінні середовища

Використовуйте готові файли з каталогу `postman/`:

- `postman/TestPrj_Local.postman_environment.json`
- `postman/TestPrj_API.postman_collection.json`

Імпортуйте їх у Postman (File → Import → Upload Files). Середовище вже містить:

- `base_url` – `http://localhost:8000/api`
- `bs4_url` – приклад URL товару
- `bs4_url_2` – другий приклад URL
- `search_query` – `Apple iPhone 15 128GB Black`
- `search_query_2` – другий пошуковий запит
- `product_id` – попередньо створена, але порожня змінна (тести заповнять)
- `product_id_2` – другий слот id (використовується Selenium-флоу)
- `product_code`, `manufacturer`, `price_1`, `price_2` – заповнюються зі scrape-відповідей
- `invalid_url` – невалідний URL для негативних тестів

## Які запити покриває колекція

Колекція (`TestPrj API`) містить такі групи:

### 00) Init

- Ініціалізує детерміновані змінні запуску (генерує `run_id`, `manual_code_*`, `manual_name_*`).

### 01) CRUD (manual deterministic)

- Створює 2 товари через `POST /products/` з прогнозованими `product_code` та `price`.
- Перевіряє:
  - список з `product_code__icontains={{run_id}}`
  - сортування за `price`
  - фільтр `min_price`
  - пагінацію та `page_size`

Цей блок навмисно не залежить від парсерів, щоб тести фільтрів/сортування були стабільні.

### 02) Scrape (parsers)

- `POST /products/scrape/bs4/` (двічі: очікуємо `201`, потім `200` зі стабільним id)
- `POST /products/scrape/selenium/`
- `POST /products/scrape/playwright/`

### 03) Export

- `GET /products/export-csv/` з фільтрами та сортуванням, перевіряє:
  - `Content-Type` це CSV
  - вивід містить раніше створені manual codes
  - застосовується сортування

### 99) Negative cases

- Відсутні/невалідні payload-и для scrape-ендпоінтів (очікуємо `400`).

## Запуск колекції

### Postman UI

- Оберіть environment (`TestPrj Local`)
- Натисніть **Run collection**
- Запускайте послідовно (рекомендовано)

### Newman (CLI)

```bash
npm install -g newman
newman run postman/TestPrj_API.postman_collection.json \
  -e postman/TestPrj_Local.postman_environment.json
```

## Примітки

- Selenium/Playwright scrape залежить від наявності браузера/драйверів на машині, де запущений API.
- Export-ендпоінт підтримує ті ж фільтри/ordering, що й list-ендпоінт.

# Сервіс парсингу товарів Brain – Backend

> Стек Django + DRF, що збирає дані з **brain.com.ua**, нормалізує їх у PostgreSQL
> та надає документований REST API (Swagger & ReDoc) для CRUD-операцій, запуску
> парсерів і експорту CSV.

---

## Зміст

1. [Огляд архітектури](#огляд-архітектури)
2. [Стек технологій](#стек-технологій)
3. [Структура репозиторію](#структура-репозиторію)
4. [Клонування та локальний запуск](#клонування-та-локальний-запуск)
5. [Запуск через Docker Compose](#запуск-через-docker-compose)
6. [Налаштування середовища](#налаштування-середовища)
7. [База даних і статика](#база-даних-і-статика)
8. [Доступ до API та Swagger](#доступ-до-api-та-swagger)
9. [Робота з API](#робота-з-api)
10. [Пряме використання парсерів](#пряме-використання-парсерів)
11. [Тестування та якість](#тестування-та-якість)
12. [Вирішення проблем](#вирішення-проблем)

---

## Огляд архітектури

```
┌────────────┐    HTTP/JSON     ┌──────────────┐
│ Swagger UI │ ───────────────► │ Django + DRF │
└────┬───────┘                  │ (parser_app) │
     │                          └────┬─────────┘
     │ parser_type у запиті        │
     │                              ▼
     │                      ┌──────────────┐
     │                      │ Шар парсерів │◄─────────┐
     │                      │ (BS4 / Sel / │          │
     │                      │  Playwright) │          │
     │                      └────┬─────────┘          │
     │                           │ ProductData        │
     │                           ▼                    │
     │                    ┌──────────────┐            │
     └────────────────────│ PostgreSQL   │◄───────────┘
                          └──────────────┘
```

- **parser_app** – бізнес-логіка (серіалізатори, в’юхи, фільтри, фабрика парсерів).
- **Парсери** – адаптери BeautifulSoup, Selenium, Playwright поверх `BrainProductParser`.
- **API** – DRF-ендпоінти для списків, створення, експорту та запуску скрейперів.
- **Документація** – `drf-yasg` піднімає Swagger (`/api/doc/`) і ReDoc (`/api/redoc/`).
- **Docker** – `docker-compose.yml` піднімає PostgreSQL, веб-додаток і опційний Nginx.

## Стек технологій

- Python 3.12, Django 5, Django REST Framework
- PostgreSQL 14
- Docker / Docker Compose
- BeautifulSoup, Selenium, Playwright (опційно)
- pytest, pytest-django, drf-yasg, Django Filters, pandas

## Структура репозиторію

```
config/                # Налаштування Django + маршрути Swagger
parser_app/            # Моделі, серіалізатори, в’юхи, тести
parser_app/parsers/    # Реалізації парсерів (bs4/selenium/playwright)
parser_app/services/   # Утиліти та фабрика парсерів
parser_app/tests/      # Pytest + DRF APIClient
nginx/                 # Конфігурація зворотного проксі
docker-compose.yml     # Композиція сервісів
pytest.ini             # Налаштування pytest
```

## Клонування та локальний запуск

```powershell
git clone https://github.com/VadimPonomarov/TestPrj.git
Set-Location TestPrj
Copy-Item .env.example .env      # оновіть креденшіали БД
poetry install
poetry run python manage.py migrate
poetry run python manage.py runserver 0.0.0.0:8000
```

Корисні команди:

- `poetry run python manage.py createsuperuser`
- `poetry run python manage.py collectstatic`
- `poetry run python manage.py wait_db --timeout=60 --interval=1`

## Запуск через Docker Compose

Передумови: Docker ≥ 24, Compose v2, налаштований `.env`.

```powershell
git clone https://github.com/VadimPonomarov/TestPrj.git
Set-Location TestPrj
Copy-Item .env.example .env
docker compose up --build
```

| Сервіс | Порт | Призначення |
| ------ | ---- | ----------- |
| `db`   | 5434 | PostgreSQL 14 з healthcheck |
| `web`  | 8000 | Django-додаток |
| `nginx`| 80   | Проксі + статичні файли |

При першому старті автоматично виконуються міграції та збір статиків. Зупинка зі знищенням томів: `docker compose down -v`.

## Налаштування середовища

| Змінна | Опис | Значення за замовчуванням |
| ------ | ---- | ------------------------ |
| `DJANGO_SETTINGS_MODULE` | Модуль налаштувань | `config.settings` |
| `DATABASE_URL` / `POSTGRES_*` | Доступ до БД | див. `.env.example` |
| `SWAGGER_DEFAULT_API_URL` | Базовий URL у Swagger | `http://localhost` |
| `IS_DOCKER` | Активація docker-режиму | `false` |
| `TEMP_DIR` | Тимчасова папка для CSV | `temp/` |

Для Playwright потрібна установка браузерів (`playwright install --with-deps chromium`).

## База даних і статика

```powershell
poetry run python manage.py migrate
poetry run python manage.py collectstatic
poetry run python manage.py createsuperuser
```

У Docker ці кроки виконує команда контейнера `web`. Скидання БД: `docker compose down -v && docker compose up`.

## Доступ до API та Swagger

- Напряму (web):
  - Swagger UI: `http://localhost:8000/api/doc/`
  - ReDoc: `http://localhost:8000/api/redoc/`
  - JSON/YAМL схема: `/api/doc.json`, `/api/doc.yaml`
- Через Nginx (якщо ввімкнений):
  - Swagger UI: `http://localhost/api/doc/`
  - ReDoc: `http://localhost/api/redoc/`

Головна сторінка (`/`) редіректить на Swagger.

## Робота з API

Базовий шлях: `/api/`

| Метод | Шлях | Призначення |
| ----- | ---- | ----------- |
| POST | `/products/` | Створення продукту вручну |
| GET | `/products/` | Список з пошуком, фільтрами, пагінацією |
| GET | `/products/<id>/` | Деталі продукту |
| GET | `/products/export-csv/` | Експорт CSV (підтримує ті ж фільтри/ordering, що й список) |
| POST | `/products/scrape/bs4/` | Запуск BS4 парсера |
| POST | `/products/scrape/selenium/` | Запуск Selenium парсера |
| POST | `/products/scrape/playwright/` | Запуск Playwright парсера |

### Приклад запиту на парсинг

```json
{
  "url": "https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_16_Pro_Max_256GB_Black_Titanium-p1145443.html"
}
```

Для `selenium`/`playwright` використовуйте пошуковий сценарій (запит на головній):

```json
{
  "query": "Apple iPhone 15 128GB Black"
}
```

- `bs4`: `url` обовʼязковий, `query` заборонений.
- `selenium`/`playwright`: `query` обовʼязковий, `url` ігнорується.
- Успішний виклик повертає створений/оновлений запис `Product`.

### Приклади cURL

```powershell
$body = '{"url":"https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_16_Pro_Max_256GB_Black_Titanium-p1145443.html"}'
Invoke-RestMethod -Method Post `
    -Uri "http://localhost:8000/api/products/scrape/bs4/" `
    -ContentType "application/json" `
    -Body $body

Invoke-RestMethod -Uri "http://localhost:8000/api/products/?search=iphone&ordering=-price&page_size=20" |
    ConvertTo-Json -Depth 4

Invoke-WebRequest -Uri "http://localhost:8000/api/products/export-csv/" -OutFile "products.csv"
```

## Пряме використання парсерів

```python
from parser_app.services.parsers.brain.parser import BrainProductParser, format_product_output

parser = BrainProductParser("https://brain.com.ua/ukr/...")
payload = parser.parse()
print(format_product_output(payload))
```

Повертаються поля: `name`, `product_code`, ціни, `manufacturer`, `color`, `storage`,
`review_count`, `screen_diagonal`, `display_resolution`, `images`, `characteristics`, `metadata`.

## Тестування та якість

```bash
poetry run pytest
poetry run pytest parser_app/tests/test_endpoints.py -k scrape
```

Тести використовують реальні DRF-ендпоінти (APIClient). Для покриття додайте `--cov=parser_app`.

## Вирішення проблем

| Симптом | Дія |
| ------- | --- |
| `OperationalError: could not connect to server` | Переконайтесь, що контейнер `db` запущений; збільште таймаут `wait_db`. |
| Swagger показує неправильний домен | Встановіть `SWAGGER_DEFAULT_API_URL` або відкрийте через Nginx. |
| Помилки Playwright про відсутність браузера | Виконайте `playwright install --with-deps chromium` всередині контейнера. |
| 404 для статики за Nginx | Перезапустіть `collectstatic`, перевірте монтування `static_volume`. |

---

Зворотній зв’язок: пишіть на email із Swagger або створюйте issue в GitHub.

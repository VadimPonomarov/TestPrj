# Scrapy-інтеграція для Brain Parser

Цей каталог містить Scrapy-проєкт, що напряму користується вже існуючими
парсерами (`parser_app.parsers.*`) та DRF-серіалізаторами/моделями для
збереження даних у ту саму базу, яку використовує API.

## Передумови

1. Встановлені Python 3.12+ та Poetry (або pip).
2. Залежності бекенду встановлені: `poetry install` (або `pip install -r requirements.txt`).
3. Налаштовані змінні оточення (`DJANGO_SETTINGS_MODULE`, `SQL_*`) через `.env.local` (локально) або `.env.docker` (Docker).
4. PostgreSQL запущений (локально чи через `docker compose up db web`).
5. Опційно: встановлені браузерні залежності для Selenium/Playwright парсерів.

## Локальне середовище (розробка)

Для локальної розробки з Scrapy додайте залежності.

Рекомендовано (перевірено): встановити dev-залежності (Scrapy знаходиться у групі `dev`):

```bash
poetry install --with dev

# Ініціалізувати Playwright (якщо потрібно)
playwright install
playwright install-deps
```

> **Увага:** Ці залежності встановлюються тільки для локального середовища розробки.
> Вони не будуть впливати на Docker-контейнери, оскільки Scrapy-павуки виконуються локально.

### .env.docker проти .env.local

`.env.docker` містить налаштування для Docker (`SQL_HOST=db`, `SQL_PORT=5432`). Для локальних Scrapy-запусків використовуйте `.env.local`, який підхоплюється автоматично:

```ini
# .env.local
SQL_HOST=127.0.0.1
SQL_PORT=5434          # порт, проброшений у docker-compose
SQL_DATABASE=mydb
SQL_USER=myuser
SQL_PASSWORD=mypassword
```

> Якщо на Windows у вас уже працює локальний PostgreSQL, він часто займає `5433`. У такому випадку використовуйте інший порт для Docker (у цьому проєкті: `5434`).

Таким чином Docker використовує `.env.docker`, а локальний Scrapy бере підключення з `.env.local`, без ручного перевизначення змінних у PowerShell.

> Кожен павук пише логіку у БД через `ProductSerializer`, тож міграції
> (`python manage.py migrate`) мають бути застосовані перед запуском.

## Структура

```
scrapy_project/
├── scrapy.cfg              # Вхідна точка для команди `scrapy`
├── brain_scraper/
│   ├── django_setup.py     # Підключення Django-контексту
│   ├── items.py            # Опис `ProductItem`
│   ├── pipelines.py        # Використання `ProductSerializer`
│   ├── settings.py         # Налаштування Scrapy (UA, конвеєр тощо)
│   ├── utils.py            # Підтягування дефолтних URL/запитів
│   └── spiders/
│       ├── base.py         # Спільна логіка, викликає `get_parser`
│       ├── bs4_spider.py   # BeautifulSoup
│       ├── selenium_spider.py
│       └── playwright_spider.py
```

## Приклади запуску

### 1. Наповнити базу даних

```powershell
Set-Location scrapy_project
$env:DJANGO_SETTINGS_MODULE = "config.settings"
scrapy crawl brain_bs4 -a "urls=https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_16_Pro_Max_256GB_Black_Titanium-p1145443.html"
```

- `brain_bs4` використовує класичний BeautifulSoup-парсер.
- Якщо `urls` не передавати, павук візьме дефолт з `ProductScrapeRequestSerializer`.
- Можна перелічити кілька URL через кому.

Інші павуки:

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings"
scrapy crawl brain_selenium -a "query=Apple iPhone 15 128GB Black"

$env:DJANGO_SETTINGS_MODULE = "config.settings"
scrapy crawl brain_playwright -a "query=Apple iPhone 15 128GB Black"
```

> Selenium/Playwright вимагають встановлених драйверів/браузерів.

### 2. Зберегти результати у файл (JSON/CSV)

За замовчуванням Scrapy експортує результати у CSV:

- `outputs/%(name)s_%(time)s.csv` (префікс = імʼя павука)

Щоб перевизначити формат/файл, використайте змінні оточення.

Scrapy підтримує експорти напряму. Наприклад, JSON:

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings"
$env:SCRAPY_FEED_URI = "outputs/bs4.json"
$env:SCRAPY_FEED_FORMAT = "json"
scrapy crawl brain_bs4
```

CSV:

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings"
$env:SCRAPY_FEED_URI = "outputs/bs4.csv"
$env:SCRAPY_FEED_FORMAT = "csv"
scrapy crawl brain_bs4
```

### 3. Перевірити через API

Після виконання павука, дані одразу доступні для DRF-ендпоінтів.

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/products/?ordering=-created_at" | ConvertTo-Json -Depth 4
Invoke-WebRequest -Uri "http://localhost:8000/api/products/export-csv/" -OutFile "temp/products.csv"
```

API та Scrapy користуються однією моделлю `Product`, тому додаткових кроків
не потрібно.

## Чейнінг / кастомні сценарії

- У `BrainParserSpider` можна перевизначити `start_requests` чи `handle_error`
  для побудови складніших workflow (наприклад, пошук по `query` перед уточненням URL).
- Можна комбінувати Scrapy Request -> обробка HTML -> виклик наших сервісних
  парсерів (що ми вже робимо через `get_parser`).
- Для батчових задач використовуйте `urls` або додайте власний аргумент і
  оновіть `resolve_targets`.

## Тестування

1. Переконайтесь, що всі Python-залежності інстальовані (`poetry install`).
2. Запустіть `poetry run pytest parser_app/tests -k scrape` — тести перевіряють
   логіку DRF-ендпоінтів, якою користується й Scrapy.
3. Для ручного smoke-тесту (перевірено):
   - Підніміть лише БД (Docker): `docker compose up -d db`
   - Переконайтесь, що Django бачить БД: `poetry run python manage.py wait_db --timeout=30 --interval=1`
   - Застосуйте міграції: `poetry run python manage.py migrate --noinput`
   - Запустіть павука через Poetry:
     ```powershell
     Set-Location scrapy_project
     poetry run scrapy crawl brain_bs4 -a "urls=https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_16_Pro_Max_256GB_Black_Titanium-p1145443.html"
     ```
   - Перевірте, що дані збережені (приклад):
     ```powershell
     poetry run python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); import django; django.setup(); from parser_app.models import Product; print(Product.objects.count())"
     ```

> Для швидкої перевірки того, що нічого не зламалося (без зовнішніх HTTP-запитів),
> використовуйте `scrapy list` та `scrapy check`.

> Якщо тестовий запуск падає через `ModuleNotFoundError: django`, переконайтесь,
> що активоване віртуальне середовище/Poetry shell або використовуйте `poetry run ...`.

## Поширені проблеми

| Симптом                                   | Рішення                                                                                                   |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `ModuleNotFoundError: django` при `scrapy crawl` | Використайте `poetry run scrapy ...` або активуйте venv, де встановлено Django.                           |
| Помилки Playwright / Selenium             | Встановіть потрібні драйвери: `playwright install --with-deps chromium`, `pip install selenium` + chromedriver. |
| Дані не зберігаються                      | Перевірте лог пайплайна (`Persisted product ...`). Якщо є помилки — вони з’являться у логах Scrapy/DRF.    |
| БД пуста після Scrapy                     | Перевірте, чи підключена та сама база що й у API (`DATABASE_URL`).                                        |
| Помилки при копіюванні команд у PowerShell| Використовуйте чисті рядки без `\`, або застосовуйте PowerShell-продовження `` ` ``.                     |

## Подальша робота

- Додайте власні пайплайни (наприклад, дедуплікацію перед DRF). 
- Підніміть `CONCURRENT_REQUESTS`/`DOWNLOAD_DELAY` для масових запусків. 
- Використовуйте `SCRAPY_FEED_URI` для одночасного експорту в кілька форматів.

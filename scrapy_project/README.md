# Brain Scraper — інструкція з запуску через CLI

У цьому файлі зібрано все необхідне для запуску Scrapy-павуків із каталогу `scrapy_project`: змінні середовища, готові команди та поради з відлагодження.

> Усі приклади команд розраховані на те, що ви перебуваєте в корені репозиторію (`D:/myDocuments/studying/Projects/TestPrj`).

## 0. Швидкий старт (одним копіпастом)

```powershell
$env:DJANGO_SETTINGS_MODULE="config.settings"; $env:PYTHONPATH=(Resolve-Path ".").Path; Push-Location ".\scrapy_project"; poetry run scrapy crawl brain_playwright -O "temp/assignment/outputs/smoke_scrapy_playwright.json" -s CLOSESPIDER_ITEMCOUNT=1 -s CLOSESPIDER_TIMEOUT=180 -s LOG_LEVEL=INFO; Pop-Location
```

## 1. Попередні кроки

1. **Встановити залежності**
   ```powershell
   poetry install
   ```
2. **Один раз встановити браузери Playwright**
   ```powershell
   poetry run playwright install chromium
   ```
3. **Налаштувати змінні середовища** (у PowerShell або `.env`):
   ```powershell
   $env:DJANGO_SETTINGS_MODULE="config.settings"
   $env:PYTHONPATH=(Resolve-Path ".").Path
   ```
4. **База даних**
   За замовчуванням використовується SQLite, додаткові дії не потрібні.

   Якщо ви очікуєте, що Scrapy буде **зберігати дані в БД** через `brain_scraper.pipelines.ProductPersistencePipeline`, то база має бути:
   - **запущена** (локально або в Docker),
   - **підключена через налаштування** (`.env*`/`config/settings.py`), щоб Django міг встановити з’єднання.

## 2. Швидкий smoke-прогін

Щоб переконатися, що все працює, запустіть кожного павука з `CLOSESPIDER_ITEMCOUNT=1` та невеликим тайм-аутом. Кожна команда експортує JSON (а через налаштування FEEDS — ще й CSV), тому можна перевіряти результат без запису до БД.

### BS4
```powershell
$env:DJANGO_SETTINGS_MODULE="config.settings"; $env:PYTHONPATH=(Resolve-Path ".").Path; Push-Location ".\scrapy_project"; poetry run scrapy crawl brain_bs4 -O "temp/assignment/outputs/smoke_scrapy_bs4.json" -s CLOSESPIDER_ITEMCOUNT=1 -s CLOSESPIDER_TIMEOUT=60 -s LOG_LEVEL=INFO; Pop-Location
```

### Selenium
```powershell
$env:DJANGO_SETTINGS_MODULE="config.settings"; $env:PYTHONPATH=(Resolve-Path ".").Path; Push-Location ".\scrapy_project"; poetry run scrapy crawl brain_selenium -O "temp/assignment/outputs/smoke_scrapy_selenium.json" -s CLOSESPIDER_ITEMCOUNT=1 -s CLOSESPIDER_TIMEOUT=180 -s LOG_LEVEL=INFO; Pop-Location
```

### Playwright
```powershell
$env:DJANGO_SETTINGS_MODULE="config.settings"; $env:PYTHONPATH=(Resolve-Path ".").Path; Push-Location ".\scrapy_project"; poetry run scrapy crawl brain_playwright -O "temp/assignment/outputs/smoke_scrapy_playwright.json" -s CLOSESPIDER_ITEMCOUNT=1 -s CLOSESPIDER_TIMEOUT=180 -s LOG_LEVEL=INFO; Pop-Location
```

При необхідності збільшуйте кількість елементів чи тайм-аут — наведені значення лише гарантують обмежений час виконання під час розробки.

## 3. Запуск окремих павуків

### 3.1 `brain_bs4`
- **Призначення:** отримати HTML готових product-URL (Requests + parsel).
- **Аргументи:** необов’язковий `urls` (список через кому). Якщо не вказувати — беруться дефолти з `parser_app.serializers.ProductScrapeRequestSerializer`.
- **Приклад:**
  ```powershell
  $env:DJANGO_SETTINGS_MODULE="config.settings"; $env:PYTHONPATH=(Resolve-Path ".").Path; Push-Location ".\scrapy_project"; poetry run scrapy crawl brain_bs4 -a urls="https://brain.com.ua/ukr/Mobilniy_telefon_Apple_iPhone_16_Pro_Max_256GB_Black_Titanium-p1145443.html" -O "outputs/bs4_run.json" -s CLOSESPIDER_TIMEOUT=120; Pop-Location
  ```

### 3.2 `brain_selenium`
- **Призначення:** головна сторінка → пошук → перший товар у headless-браузері з блокуванням медіа.
- **Аргументи:** необов’язковий `query` (дефолт читається з `DEFAULT_QUERY`).
- **Приклад:**
  ```powershell
  $env:DJANGO_SETTINGS_MODULE="config.settings"; $env:PYTHONPATH=(Resolve-Path ".").Path; Push-Location ".\scrapy_project"; poetry run scrapy crawl brain_selenium -a query="Apple iPhone 15 128GB Black" -O "outputs/selenium_run.json" -s CLOSESPIDER_ITEMCOUNT=2 -s CLOSESPIDER_TIMEOUT=240; Pop-Location
  ```

### 3.3 `brain_playwright`
- **Призначення:** той самий сценарій, але через Playwright Chromium.
- **Аргументи:** необов’язковий `query`.
- **Приклад:**
  ```powershell
  $env:DJANGO_SETTINGS_MODULE="config.settings"; $env:PYTHONPATH=(Resolve-Path ".").Path; Push-Location ".\scrapy_project"; poetry run scrapy crawl brain_playwright -a query="Apple iPhone 15 128GB Black" -O "outputs/playwright_run.json" -s CLOSESPIDER_ITEMCOUNT=2 -s CLOSESPIDER_TIMEOUT=240; Pop-Location
  ```

## 4. Корисні змінні середовища

| Змінна | Значення за замовчуванням | Опис |
| --- | --- | --- |
| `SCRAPY_DOWNLOAD_DELAY` | `0.5` | Глобальна затримка між запитами (секунди). |
| `SCRAPY_CONCURRENT_REQUESTS` | `4` | Загальна кількість одночасних запитів. |
| `SCRAPY_DOWNLOAD_TIMEOUT` | `30` | Тайм-аут на завантаження (секунди). |
| `SCRAPY_CLOSESPIDER_TIMEOUT` | unset | Зупинка павука після N секунд роботи. |
| `SCRAPY_CLOSESPIDER_ITEMCOUNT` | unset | Зупинка після N зібраних елементів. |
| `SCRAPY_CLOSESPIDER_PAGECOUNT` | unset | Зупинка після N отриманих відповідей. |
| `SCRAPY_BS4_DOWNLOAD_DELAY` | `0.5` | Перевизначення для `brain_bs4`. |
| `SCRAPY_SELENIUM_DOWNLOAD_DELAY` | `0.5` | Перевизначення для Selenium-павука. |
| `SCRAPY_SELENIUM_CONCURRENT_REQUESTS` | `1` | Конкурентність Selenium (утримується =1). |
| `SCRAPY_SELENIUM_CLOSESPIDER_TIMEOUT` | `180` | Типовий ліміт часу Selenium-павука. |
| `SCRAPY_PLAYWRIGHT_CLOSESPIDER_TIMEOUT` | `180` | Аналогічний ліміт для Playwright. |

Перед запуском просто задайте їх:
```powershell
$env:SCRAPY_CLOSESPIDER_ITEMCOUNT="3"; $env:DJANGO_SETTINGS_MODULE="config.settings"; $env:PYTHONPATH=(Resolve-Path ".").Path; Push-Location ".\scrapy_project"; poetry run scrapy crawl brain_playwright -O "outputs/run.json"; Pop-Location
```

## 5. Куди пишеться результат

- JSON зберігається у файл, переданий через `-O/--output`, а CSV — автоматично у `outputs/brain_<spider>_<timestamp>.csv` (див. `FEEDS` у `brain_scraper/settings.py`).
- `brain_scraper.pipelines.ProductPersistencePipeline` паралельно пише валідні елементи в Django-БД (модель `parser_app.models.Product`).

## 6. Поради з відлагодження

1. **Помилки драйверів Selenium/Playwright**
   - Перевірте, що Chrome/Chromium встановлено.
   - Якщо версії не збігаються, можна очистити кеш драйверів (за потреби):
     ```powershell
     Remove-Item -Recurse -Force "$env:USERPROFILE\.wdm"
     ```
2. **Проблеми Playwright на Windows**
   - У павуку вже встановлюється відповідна `asyncio` policy, але у власних скриптах не забудьте про `WindowsProactorEventLoopPolicy`.
3. **Тайм-аути / зависання**
   - Підніміть `CLOSESPIDER_TIMEOUT` або `DOWNLOAD_TIMEOUT` через `-s` чи env.
   - Для Selenium/Playwright працює fallback: якщо клік не спрацював, павук відкриває `/search/` напряму.
4. **Помилки валідації пайплайну**
   - Обов’язкові поля: `name`, `product_code`, `source_url`, `price`. Якщо чогось бракує, пайплайн логуватиме помилку і пропускатиме запис у БД.

## 7. Рекомендований регрес

1. `poetry run python manage.py check`
2. `poetry run pytest -q`
3. Виконати три smoke-команди з розділу 2.
4. Перевірити `outputs/*.csv` та/або JSON-файли.

Після такого сценарію можна бути впевненим, що павуки, Django-API та збереження працюють разом.

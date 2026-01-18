# Посібник з деплойменту (TestPrj)

Цей документ описує всі варіанти запуску бекенду Brain Product Parser після клонування репозиторію.

---

## 1. Передумови

1. **Docker Desktop / Docker Engine** v24+ (разом із плагіном Docker Compose V2). Docker має бути встановлений, запущений та авторизований перед стартом будь-якого сценарію деплою, інакше контейнеризація не розпочнеться.
2. **Python 3.12+** (потрібен лише для допоміжного скрипта).
3. **Git** для клонування.
4. Порти `5434`, `8000`, `80` мають бути вільними на хості.

> Усі файли середовища (`.env`, `.env.local` тощо) входять до репозиторію, щоб нові інсталяції одразу мали адекватні значення за замовчуванням. Налаштуйте секрети після клонування.

---

## 2. Швидкий шлях: `deploy.py`

Перебуваючи в корені проєкту, виконайте:

```powershell
python deploy.py
```

Що відбувається:

1. Перевіряється наявність Docker/Docker Compose.
2. Створюються відсутні `.env` / `.env.local` із безпечними значеннями (файли відстежуються в git).
3. Скрипт перевіряє, чи існують у Docker контейнери/мережі/томи з конфліктними назвами. Якщо такі елементи знайдено, зʼявляється меню вибору: можна видалити конкретний ресурс, усі одразу або вийти з деплою.
4. Після усунення конфліктів виконується `docker compose up -d --build db web nginx`.
5. Очікується, поки контейнери PostgreSQL і Django стануть здоровими.
6. Виводяться наступні команди (логи, сценарій лише для БД, інструкції для Scrapy).

### Необовʼязкові прапорці

```powershell
python deploy.py --db-only     # запуск лише контейнера PostgreSQL (локальний режим Scrapy)
python deploy.py --skip-build  # повторне використання зібраних Docker-образів
python deploy.py --no-wait     # не чекати перевірок здоровʼя
```

---

## 3. Ручний деплоймент (класичний Docker Compose)

```powershell
git clone https://github.com/VadimPonomarov/TestPrj.git
Set-Location TestPrj
Copy-Item .env.example .env           # за потреби відредагуйте облікові дані
docker compose up -d --build          # запускає db + web + nginx
```

Корисні подальші команди:

```powershell
docker compose logs -f web            # стрічка логів Django
docker compose exec web python manage.py createsuperuser
docker compose down -v                # зупинка контейнерів і видалення томів
```

### Порти

| Сервіс | Порт хоста | Примітки |
| ------- | --------- | ----- |
| db      | 5434      | PostgreSQL 14 (проксі з 5432 контейнера) |
| web     | 8000      | Django-додаток (Swagger за `/api/doc/`) |
| nginx   | 80        | Необовʼязковий реверс-проксі |

---

## 4. Робочий процес «лише БД» для локального Scrapy

1. Запустіть лише контейнер бази даних:

   ```powershell
   docker compose up -d db
   ```

2. Запустіть Scrapy локально (приклад для PowerShell):

   ```powershell
   Set-Location scrapy_project
   $env:DJANGO_SETTINGS_MODULE = "config.settings"
   scrapy crawl brain_bs4 -O output.json
   ```

Файл `.env.local` (відстежується) вже вказує Scrapy на `127.0.0.1:5434`.

---

## 5. Чекліст перевірки

- `http://localhost:8000/api/products/` повертає JSON (порожній список після першого запуску).
- `http://localhost:8000/api/doc/` показує Swagger UI.
- `docker compose ps` показує всі контейнери у стані `running`.
- Запуск Scrapy створює `scrapy_project/output.json` і вставляє рядок у базу.

---

## 6. Усунення несправностей

| Симптом | Рішення |
| ------- | ---- |
| `docker compose` не може стягнути образи | Перелогіньтесь у Docker Hub або перевірте мережу. |
| `UnicodeDecodeError` під час локального Scrapy | Запускайте через виртуальне середовище репозиторію та переконайтеся, що `.env.local` присутній (кодування PG клієнта налаштоване). |
| `psycopg` не підʼєднується | Переконайтеся, що Docker-БД слухає порт `5434` і локальний Postgres не займає його. |
| 404 для Django admin/login | Виконайте `docker compose exec web python manage.py createsuperuser`, щоб створити користувача. |
| Потрібно скинути базу | `docker compose down -v && docker compose up -d --build`. |

Для додаткового контексту (парсери, використання API, інструкції Scrapy) зверніться до `README.md`
та `scrapy_project/README.uk.md`.

# Посібник з деплойменту (TestPrj)

Цей документ описує всі варіанти запуску бекенду Brain Product Parser після клонування репозиторію.

---

## 0. Клонування репозиторію

```powershell
git clone https://github.com/VadimPonomarov/TestPrj.git
Set-Location TestPrj
```

> Усі шляхи й команди нижче припускають, що ви перебуваєте у корені свіжого клону.

---

## 1. Передумови

| Сценарій                              | Обовʼязкові залежності                               | Додаткові вимоги                                     |
| ------------------------------------- | --------------------------------------------------- | ---------------------------------------------------- |
| Docker (рекомендовано)                | Docker Desktop / Engine v24+ з Compose V2, Git       | Вільні порти `80`, `8000`, `5434`                    |
| `deploy.py`                           | Docker + Compose V2, Python 3.12+ на хості           | `python --version` ⇒ `3.12.x`                        |
| `deploy.local.py` / ручний локальний запуск | Python 3.12+, [Poetry](https://python-poetry.org/), локальний PostgreSQL або Docker-БД | `poetry --version` ≥ 2.2, доступ до `psql` (бажано) |

### Швидкі перевірки

```powershell
python --version          # очікуємо 3.12.x
poetry --version          # для локального запуску без Docker
docker --version          # ≥ 24.x
docker compose version    # Compose V2
```

> Нотатки:
> - Для Docker використовується `.env.docker`.
> - Для локального запуску використовується `.env.local`.
> - Усі шляхи й команди нижче припускають, що ви перебуваєте у корені свіжого клону.

---

## 2. Швидкий шлях: `deploy.py`

Найзручніший сценарій: один скрипт готує `.env`, запускає Docker stack та перевіряє здоровʼя сервісів.

Перебуваючи в корені проєкту, виконайте:

```powershell
python deploy.py
```

Що відбувається:

1. Перевіряється наявність Docker/Docker Compose.
2. Створюються відсутні `.env.docker` / `.env.local` із безпечними значеннями.
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

Підходить, якщо потрібно більше контролю над кожним кроком або CI/CD інтеграція.

```powershell
git clone https://github.com/VadimPonomarov/TestPrj.git
Set-Location TestPrj
# за потреби відредагуйте .env.docker
docker compose up -d --build          # запускає db + web + nginx
```

Корисні подальші команди:

```powershell
docker compose logs -f web            # стрічка логів Django
docker compose exec web python manage.py createsuperuser
docker compose down -v                # зупинка контейнерів і видалення томів
```

### Порти

| Сервіс | Порт хоста | Примітки                                  |
| ------ | ---------- | ----------------------------------------- |
| `db`   | `5434`     | PostgreSQL 14 (проксі з 5432 контейнера)  |
| `web`  | `8000`     | Django-додаток (Swagger за `/api/doc/`)   |
| `nginx`| `80`       | Необовʼязковий реверс-проксі              |

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

## 6. Локальний запуск без Docker: `deploy.local.py`

Цей сценарій корисний для швидкої розробки/дебагу без контейнерів.

### Передумови

1. **Python 3.12+** (перевірте `python --version`/`py --version`).
2. **Poetry 2.2+** (установіть через `curl -sSL https://install.python-poetry.org | python3 -` або PowerShell-аналог; потім додайте шлях до `PATH`).
3. **PostgreSQL**:
   - локальна інстанція на `127.0.0.1:5432`, **або**
   - контейнер `db` з Docker-compose, що проброшений на `127.0.0.1:5434`.

### Швидкий старт

Перебуваючи в корені проєкту:

```powershell
python deploy.local.py
```

Скрипт:

1. Перевіряє Python/Poetry.
2. Створює відсутній `.env.local` (не перезаписуючи існуючий).
3. Запускає `poetry install`.
4. Чекає готовність PostgreSQL (`manage.py wait_db`).
5. Виконує `migrate` та `collectstatic`.
6. Запускає `runserver`.

Після старту:

- Swagger UI: `http://127.0.0.1:8000/api/doc/`
- API: `http://127.0.0.1:8000/api/`

### Поширені варіанти

#### 1) Якщо PostgreSQL працює на іншому порту/з іншими кредами

```powershell
python deploy.local.py --db-host 127.0.0.1 --db-port 5432 --db-name mydb --db-user myuser --db-password mypassword
```

#### 2) Використати Docker-БД, але запускати Django локально
 
  Цей сценарій потрібен, коли **PostgreSQL крутиться в Docker**, але **Django запускається на хості** (Windows/macOS/Linux).
 
  Важливо:
  - Імʼя сервісу з `docker-compose.yml` (наприклад, `db`) працює **тільки всередині Docker мережі**.
  - З хоста підключення має йти на **`127.0.0.1` + порт пробросу** (у цьому проєкті це `5434`).
 
  1. Запустіть тільки контейнер БД:
 
     ```powershell
     docker compose up -d db
     ```
 
  2. Переконайтесь, що порт проброшено:
 
     - у `docker-compose.yml` має бути мапінг `"5434:5432"` для `db`
     - команда `docker compose ps` має показати `db` у стані `running`
 
  3. Вкажіть підключення у `.env.local`:
 
     ```env
     SQL_HOST=127.0.0.1
     SQL_PORT=5434
     SQL_DATABASE=mydb
     SQL_USER=myuser
     SQL_PASSWORD=mypassword
     ```
 
     Не використовуйте в `.env.local`:
     - `SQL_HOST=db` (працює тільки всередині Docker)
     - `SQL_HOST=mydb` (це назва БД, а не хост)
 
  4. Запустіть локальний деплой:
 
     ```powershell
     python deploy.local.py
     ```
 
     Або (якщо хочете явно перевизначити параметри без редагування `.env.local`):
 
     ```powershell
     python deploy.local.py --db-host 127.0.0.1 --db-port 5434
     ```
 
  5. Швидка перевірка підключення (опційно):
 
     ```powershell
     poetry run python manage.py wait_db --timeout=10 --interval=1
     ```

### Примітки

- `.env.local` відстежується в репозиторії та містить дефолтні налаштування для локального режиму. За потреби змініть значення під свій стенд.
- Якщо в системі вже встановлений PostgreSQL, переконайтесь, що порт `5432` не зайнятий іншою інстанцією (і що Docker не використовує `5434` одночасно).
- Для Windows-консолей можна уникнути Unicode-помилок, задавши `set PYTHONIOENCODING=utf-8` перед запуском скриптів.

---
## 7. Усунення несправностей

| Симптом                              | Рішення                                                                                                       |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| `docker compose` не може стягнути образи | Перелогіньтесь у Docker Hub або перевірте мережу.                                                             |
| `UnicodeDecodeError` під час локального Scrapy | Запускайте через виртуальне середовище репозиторію та переконайтеся, що `.env.local` присутній (кодування PG клієнта налаштоване). |
| `psycopg` не підʼєднується            | Переконайтеся, що Docker-БД слухає порт `5434` і локальний Postgres не займає його.                           |
| 404 для Django admin/login            | Виконайте `docker compose exec web python manage.py createsuperuser`, щоб створити користувача.              |
| Потрібно скинути базу                 | `docker compose down -v && docker compose up -d --build`.                                                     |

Для додаткового контексту (парсери, використання API, інструкції Scrapy) зверніться до `README.md`
та `scrapy_project/README.md`.

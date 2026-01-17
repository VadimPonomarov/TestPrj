# Deployment Guide (TestPrj)

This document describes every option for spinning up the Brain Product Parser backend
after cloning the repository.

---

## 1. Prerequisites

1. **Docker Desktop / Docker Engine** v24+ (with Docker Compose V2 plugin).
2. **Python 3.11+** (needed only for the helper script).
3. **Git** for cloning.
4. Ports `5434`, `8000`, `80` must be available on the host.

> All environment files (`.env`, `.env.local`, etc.) are part of the repository so
> that new environments have sane defaults immediately. Adjust secrets after cloning.

---

## 2. Fast path: `deploy.py`

Once you are in the project root, run:

```powershell
python deploy.py
```

What happens:

1. Confirms Docker/Docker Compose are installed.
2. Creates missing `.env` / `.env.local` with safe defaults (tracked in git).
3. Runs `docker compose up -d --build db web nginx`.
4. Waits for PostgreSQL + Django containers to become healthy.
5. Prints follow-up commands (logs, db-only workflow, Scrapy instructions).

### Optional flags

```powershell
python deploy.py --db-only     # start only the PostgreSQL container (local Scrapy mode)
python deploy.py --skip-build  # reuse existing Docker images
python deploy.py --no-wait     # do not wait for health checks
```

---

## 3. Manual deployment (classic Docker Compose)

```powershell
git clone https://github.com/VadimPonomarov/TestPrj.git
Set-Location TestPrj
Copy-Item .env.example .env           # optional, adjust credentials if needed
docker compose up -d --build          # spins up db + web + nginx
```

Useful follow-ups:

```powershell
docker compose logs -f web            # tail Django logs
docker compose exec web python manage.py createsuperuser
docker compose down -v                # stop and remove volumes
```

### Ports

| Service | Host port | Notes |
| ------- | --------- | ----- |
| db      | 5434      | PostgreSQL 14 (mapped from container 5432) |
| web     | 8000      | Django app (Swagger at `/api/doc/`) |
| nginx   | 80        | Optional reverse proxy |

---

## 4. DB-only workflow for local Scrapy

1. Start only the database container:

   ```powershell
   docker compose up -d db
   ```

2. Run Scrapy locally (PowerShell example):

   ```powershell
   Set-Location scrapy_project
   $env:DJANGO_SETTINGS_MODULE = "config.settings"
   scrapy crawl brain_bs4 -O output.json
   ```

The `.env.local` file (tracked) already points Scrapy to `127.0.0.1:5434`.

---

## 5. Verification checklist

- `http://localhost:8000/api/products/` returns JSON (empty list after fresh run).
- `http://localhost:8000/api/doc/` shows Swagger UI.
- `docker compose ps` shows all containers in `running` state.
- Scrapy run produces `scrapy_project/output.json` and inserts a row into the DB.

---

## 6. Troubleshooting

| Symptom | Fix |
| ------- | ---- |
| `docker compose` cannot pull images | Re-login to Docker Hub or check network. |
| `UnicodeDecodeError` during local Scrapy | Ensure you run via the repo's virtualenv and `.env.local` is in place (PG client encoding is handled automatically). |
| `psycopg` cannot connect | Make sure Docker DB is on port `5434` and no local Postgres instance occupies the same port. |
| Django admin/login 404 | Run `docker compose exec web python manage.py createsuperuser` to create credentials. |
| Need to reset database | `docker compose down -v && docker compose up -d --build`. |

For additional context (parsers, API usage, Scrapy instructions) refer to `README.md`
and `scrapy_project/README.uk.md`.

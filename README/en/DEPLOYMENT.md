# Deployment guide (TestPrj)

This document describes all supported ways to run the Brain Product Parser backend after cloning the repository.

---

## 0. Clone the repository

```powershell
git clone https://github.com/VadimPonomarov/TestPrj.git
Set-Location TestPrj
```

> All paths and commands below assume you are in the repository root.

---

## 1. Prerequisites

| Scenario                               | Required dependencies                                               | Extra requirements                                      |
| -------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------- |
| Docker (recommended)                   | Docker Desktop / Engine v24+ with Compose V2, Git                    | Free ports `80`, `8000`, `5434`                         |
| `deploy.py`                            | Docker + Compose V2, Python 3.12+ on the host                        | `python --version` ⇒ `3.12.x`                           |
| `deploy.local.py` / manual local setup | Python 3.12+, [Poetry](https://python-poetry.org/), local PostgreSQL or Docker DB | `poetry --version` ≥ 2.2, `psql` available (recommended) |

### Quick checks

```powershell
python --version          # expect 3.12.x
poetry --version          # for local (non-Docker) workflow
docker --version          # ≥ 24.x
docker compose version    # Compose V2
```

> Notes:
> - Docker uses `.env.docker`.
> - Local (non-Docker) uses `.env.local`.
> - All paths and commands below assume you are in the repository root.

---

## 2. Recommended: `deploy.py`

The most convenient workflow: one helper script prepares env files, starts the Docker stack and checks service health.

Run from the repository root:

```powershell
python deploy.py
```

What it does:

1. Verifies Docker/Docker Compose availability.
2. Creates missing `.env.docker` / `.env.local` with safe defaults.
3. Detects conflicting Docker resources (containers/networks/volumes) and offers an interactive cleanup menu.
4. Runs `docker compose up -d --build db web nginx`.
5. Waits for PostgreSQL and Django to become healthy.
6. Prints follow-up commands (logs, db-only mode, Scrapy hints).

### Optional flags

```powershell
python deploy.py --db-only     # start only PostgreSQL (db-only workflow for local Scrapy)
python deploy.py --skip-build  # reuse existing images
python deploy.py --no-wait     # do not wait for health checks
```

---

## 3. Manual deployment (classic Docker Compose)

Use this if you need full control over the steps or for CI/CD.

```powershell
# from repository root
# edit .env.docker if you need custom credentials
docker compose up -d --build   # starts db + web + nginx
```

Useful follow-up commands:

```powershell
docker compose logs -f web
docker compose exec web python manage.py createsuperuser
docker compose down -v
```

### Ports

| Service | Host port | Notes                                          |
| ------- | --------- | ---------------------------------------------- |
| `db`    | `5434`    | PostgreSQL 14 (host proxy to container `5432`) |
| `web`   | `8000`    | Django app (Swagger at `/api/doc/`)            |
| `nginx` | `80`      | Optional reverse proxy                         |

---

## 4. DB-only workflow for local Scrapy

1. Start only the database container:

   ```powershell
   docker compose up -d db
   ```

2. Ensure Scrapy dependencies are installed (Scrapy is included in Poetry dev dependencies). If you install without dev deps, re-run `poetry install --with dev`. Follow `README/en/scrapy_project/README.md`.

3. Run Scrapy locally:

   ```powershell
   Set-Location scrapy_project
   $env:DJANGO_SETTINGS_MODULE = "config.settings"
   scrapy crawl brain_bs4 -O output.json
   ```

`.env.local` points Scrapy to `127.0.0.1:5434` by default.

---

## 5. Verification checklist

- `http://localhost:8000/api/products/` returns JSON (empty list on first run).
- `http://localhost:8000/api/doc/` shows Swagger UI.
- `docker compose ps` shows containers in `running` state.

Concrete smoke checks used during verification:

```powershell
Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8000/api/products/" | Select-Object StatusCode
Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8000/api/doc/" | Select-Object StatusCode
poetry run pytest -q
```

---

## 6. Local run without Docker: `deploy.local.py`

This workflow is useful for quick development/debugging without containers.

### Prerequisites

1. **Python 3.12+** (`python --version` / `py --version`).
2. **Poetry 2.2+** (dependencies are managed via `pyproject.toml`).
3. **PostgreSQL**:
   - local instance on `127.0.0.1:5432`, or
   - Docker DB on `127.0.0.1:5434` (if you run `docker compose up -d db`).

### Quickstart

```powershell
python deploy.local.py
```

The script:

1. Checks Python/Poetry.
2. Ensures `.env.local` exists (without overwriting existing values).
3. Runs `poetry install`.
4. Waits for PostgreSQL (`manage.py wait_db`).
5. Runs `migrate` and `collectstatic`.
6. Starts `runserver`.

After startup:

- Swagger UI: `http://127.0.0.1:8000/api/doc/`
- API base: `http://127.0.0.1:8000/api/`

### Common variants

#### 1) PostgreSQL on a different host/port/credentials

```powershell
python deploy.local.py --db-host 127.0.0.1 --db-port 5432 --db-name mydb --db-user myuser --db-password mypassword
```

#### 2) Use Docker DB but run Django locally

Important notes:

- Docker service name `db` works only *inside* Docker network.
- From the host you must connect to `127.0.0.1` + the published port (here: `5434`).

Steps:

1. Start only the DB container:

   ```powershell
   docker compose up -d db
   ```

2. Ensure port mapping exists (`"5434:5432"` for `db`) and container is running.

3. Set DB connection in `.env.local`:

   ```env
   SQL_HOST=127.0.0.1
   SQL_PORT=5434
   SQL_DATABASE=mydb
   SQL_USER=myuser
   SQL_PASSWORD=mypassword
   ```

4. Run local deploy:

   ```powershell
   python deploy.local.py
   ```

5. Optional quick check:

   ```powershell
   poetry run python manage.py wait_db --timeout=10 --interval=1
   ```

### Notes

- `.env.local` is tracked in the repository and contains default local settings. Adjust values for your workstation if needed.
- If PostgreSQL is already installed locally, ensure port `5432` is not occupied by another instance (and Docker does not use `5434` at the same time).

---

## 7. Troubleshooting

| Symptom                                   | Fix                                                                                               |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `docker compose` cannot pull images        | Re-login to Docker Hub or check network connectivity.                                              |
| `Bind for 0.0.0.0:5434 failed: port is already allocated` | Stop the process/container that uses `5434` (e.g., `docker ps` + `docker stop <name>`), or change the published port in `docker-compose.yml` and update `.env.local` accordingly. |
| Unicode/encoding errors in Windows console | Run scripts in a UTF-8 console or set `PYTHONIOENCODING=utf-8` before executing Python scripts.   |
| `psycopg` cannot connect                   | Ensure Docker DB is published on `5434` and local PostgreSQL is not occupying the port.            |
| 404 for Django admin/login                 | Run `docker compose exec web python manage.py createsuperuser` to create a user.                  |
| Need to reset the DB                       | `docker compose down -v && docker compose up -d --build`.                                          |

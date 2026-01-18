#!/usr/bin/env python3
"""Local (non-Docker) deployment helper for TestPrj.

This script prepares a developer workstation for running the project directly on the host:
- checks prerequisites (Python, Poetry, PostgreSQL connectivity)
- ensures `.env.local` exists (without overwriting existing values)
- installs dependencies via Poetry
- runs migrations and collectstatic
- starts Django dev server

Usage:
  python deploy.local.py

Common flags:
  --skip-install
  --skip-migrate
  --skip-collectstatic
  --no-runserver
  --db-host 127.0.0.1 --db-port 5432
  --db-name mydb --db-user myuser --db-password mypassword
  --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parent


class Colors:
    if sys.stdout.isatty():
        BLUE = "\033[94m"
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        RED = "\033[91m"
        BOLD = "\033[1m"
        DIM = "\033[2m"
        RESET = "\033[0m"
    else:
        BLUE = GREEN = YELLOW = RED = BOLD = DIM = RESET = ""


def print_header() -> None:
    banner = "=" * 64
    print(f"{Colors.BLUE}{banner}{Colors.RESET}")
    print(f"{Colors.BOLD}TestPrj Local Deployment Helper{Colors.RESET}")
    print(banner)
    print()


def print_step(index: int, message: str) -> None:
    print(f"{Colors.BLUE}[step {index}] {message}{Colors.RESET}")


def print_success(message: str) -> None:
    print(f"{Colors.GREEN}OK: {message}{Colors.RESET}")


def print_warning(message: str) -> None:
    print(f"{Colors.YELLOW}WARN: {message}{Colors.RESET}")


def print_error(message: str) -> None:
    print(f"{Colors.RED}ERROR: {message}{Colors.RESET}")


def ensure_repo_root() -> None:
    required_markers = ["pyproject.toml", "manage.py"]
    missing = [marker for marker in required_markers if not (REPO_ROOT / marker).exists()]
    if missing:
        print_error("Run this script from the repository root (missing: " + ", ".join(missing) + ")")
        raise SystemExit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local deployment helper (no Docker)")

    parser.add_argument("--skip-install", action="store_true", help="Skip `poetry install` step")
    parser.add_argument("--skip-migrate", action="store_true", help="Skip Django migrations")
    parser.add_argument("--skip-collectstatic", action="store_true", help="Skip collectstatic")
    parser.add_argument("--no-runserver", action="store_true", help="Do not start Django dev server")

    parser.add_argument("--host", default="127.0.0.1", help="runserver host (default: 127.0.0.1)")
    parser.add_argument("--port", default="8000", help="runserver port (default: 8000)")

    parser.add_argument("--db-host", default=None, help="PostgreSQL host (overrides .env.local)")
    parser.add_argument("--db-port", type=int, default=None, help="PostgreSQL port (overrides .env.local)")
    parser.add_argument("--db-name", default=None, help="PostgreSQL database name (overrides .env.local)")
    parser.add_argument("--db-user", default=None, help="PostgreSQL user (overrides .env.local)")
    parser.add_argument("--db-password", default=None, help="PostgreSQL password (overrides .env.local)")

    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="DB wait timeout in seconds (default: 60)",
    )

    return parser.parse_args()


def check_python_version(min_major: int = 3, min_minor: int = 12) -> None:
    if sys.version_info < (min_major, min_minor):
        print_error(f"Python {min_major}.{min_minor}+ is required. Current: {sys.version.split()[0]}")
        raise SystemExit(1)
    print_success(f"Python {sys.version.split()[0]}")


def require_executable(name: str, hint: str) -> None:
    if shutil.which(name) is None:
        print_error(f"Missing required executable: {name}\n{hint}")
        raise SystemExit(1)
    result = subprocess.run([name, "--version"], text=True, capture_output=True, check=False)
    if result.returncode == 0:
        print_success(result.stdout.strip())
    else:
        print_warning(f"Unable to read {name} version")


def _read_env_keys(path: Path) -> Dict[str, str]:
    keys: Dict[str, str] = {}
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return keys
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        keys.setdefault(key, value)
    return keys


def _append_missing_env_keys(path: Path, defaults: Dict[str, str]) -> List[str]:
    existing = _read_env_keys(path)
    missing = [key for key in defaults.keys() if key not in existing]
    if not missing:
        return []
    to_append = "\n" + "\n".join(f"{key}={defaults[key]}" for key in missing) + "\n"
    path.write_text(path.read_text(encoding="utf-8") + to_append, encoding="utf-8")
    return missing


def ensure_env_files(db: Dict[str, str]) -> List[str]:
    created: List[str] = []

    local_path = REPO_ROOT / ".env.local"
    if not local_path.exists():
        local_template = textwrap.dedent(
            f"""
            # Local overrides for running without Docker
            DEBUG=1
            SECRET_KEY=replace_me
            DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
            SQL_ENGINE=django.db.backends.postgresql
            SQL_HOST={db['SQL_HOST']}
            SQL_PORT={db['SQL_PORT']}
            SQL_DATABASE={db['SQL_DATABASE']}
            SQL_USER={db['SQL_USER']}
            SQL_PASSWORD={db['SQL_PASSWORD']}
            DJANGO_SETTINGS_MODULE=config.settings

            PLAYWRIGHT_PROXY_SERVER=
            PLAYWRIGHT_PROXY_USERNAME=
            PLAYWRIGHT_PROXY_PASSWORD=

            SELENIUM_PROXY_SERVER=
            """
        ).strip() + "\n"
        local_path.write_text(local_template, encoding="utf-8")
        created.append(".env.local")
    else:
        required_defaults = {
            "DEBUG": "1",
            "SECRET_KEY": "replace_me",
            "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1",
            "SQL_ENGINE": "django.db.backends.postgresql",
            "SQL_HOST": db["SQL_HOST"],
            "SQL_PORT": db["SQL_PORT"],
            "SQL_DATABASE": db["SQL_DATABASE"],
            "SQL_USER": db["SQL_USER"],
            "SQL_PASSWORD": db["SQL_PASSWORD"],
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "PLAYWRIGHT_PROXY_SERVER": "",
            "PLAYWRIGHT_PROXY_USERNAME": "",
            "PLAYWRIGHT_PROXY_PASSWORD": "",
            "SELENIUM_PROXY_SERVER": "",
        }
        missing = _append_missing_env_keys(local_path, required_defaults)
        if missing:
            print_warning(".env.local is missing keys; appended defaults: " + ", ".join(missing))

    return created


def _extract_docker_db_host_port_from_compose(compose_path: Path) -> Dict[str, str]:
    if not compose_path.exists():
        return {}

    try:
        lines = compose_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}

    in_db = False
    db_indent: int | None = None
    for raw_line in lines:
        line = raw_line.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        if line.lstrip().startswith("db:"):
            in_db = True
            db_indent = len(line) - len(line.lstrip())
            continue

        if in_db and db_indent is not None:
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= db_indent and line.strip().endswith(":"):
                in_db = False
                db_indent = None
                continue

            stripped = line.strip().strip("\"").strip("'")
            if stripped.startswith("-"):
                mapping = stripped.lstrip("-").strip().strip("\"").strip("'")
                if ":" in mapping:
                    left, right = mapping.split(":", 1)
                    left = left.strip()
                    right = right.strip()
                    if right == "5432":
                        return {"SQL_HOST": "127.0.0.1", "SQL_PORT": left}

    return {}


def _get_default_db_env_from_repo_files() -> Dict[str, str]:
    docker_env_path = REPO_ROOT / ".env.docker"
    compose_path = REPO_ROOT / "docker-compose.yml"

    docker_env = _read_env_keys(docker_env_path) if docker_env_path.exists() else {}
    compose_hint = _extract_docker_db_host_port_from_compose(compose_path)

    defaults: Dict[str, str] = {
        "SQL_HOST": "127.0.0.1",
        "SQL_PORT": "5432",
        "SQL_DATABASE": docker_env.get("SQL_DATABASE", "mydb"),
        "SQL_USER": docker_env.get("SQL_USER", "myuser"),
        "SQL_PASSWORD": docker_env.get("SQL_PASSWORD", "mypassword"),
    }
    defaults.update({k: v for k, v in compose_hint.items() if v})
    return defaults


def build_subprocess_env(db: Dict[str, str]) -> Dict[str, str]:
    env = os.environ.copy()
    env.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    env.pop("IS_DOCKER", None)
    env.update(db)
    return env


def run(cmd: List[str], *, env: Dict[str, str] | None = None) -> None:
    print(f"{Colors.DIM}$ {' '.join(cmd)}{Colors.RESET}")
    result = subprocess.run(cmd, cwd=REPO_ROOT, text=True, env=env)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def print_db_help(db: Dict[str, str]) -> None:
    print()
    print_warning("PostgreSQL is not reachable with the current settings.")
    print("Check that PostgreSQL is installed and running, and that the database/user exist.")
    print()
    print("Expected connection settings:")
    for key in ("SQL_HOST", "SQL_PORT", "SQL_DATABASE", "SQL_USER"):
        print(f"  - {key}={db[key]}")
    print()

    compose_path = REPO_ROOT / "docker-compose.yml"
    if compose_path.exists():
        docker_hint = _extract_docker_db_host_port_from_compose(compose_path)
        host = docker_hint.get("SQL_HOST", "127.0.0.1")
        port = docker_hint.get("SQL_PORT")
        print("If your PostgreSQL is running in Docker:")
        print("  1) Start it: docker compose up -d db")
        if port:
            print("  2) Use host connection (service name 'db' works only inside Docker):")
            print(f"     SQL_HOST={host}")
            print(f"     SQL_PORT={port}")
        print()

    print("Example psql commands (run in an elevated shell if required):")
    print(textwrap.dedent(
        f"""
        psql -h {db['SQL_HOST']} -p {db['SQL_PORT']} -U postgres

        -- in psql:
        CREATE USER {db['SQL_USER']} WITH PASSWORD '{db['SQL_PASSWORD']}';
        CREATE DATABASE {db['SQL_DATABASE']} OWNER {db['SQL_USER']};
        GRANT ALL PRIVILEGES ON DATABASE {db['SQL_DATABASE']} TO {db['SQL_USER']};
        """
    ).strip())
    print()


def main() -> None:
    args = parse_args()
    print_header()
    ensure_repo_root()

    print_step(1, "Checking prerequisites")
    check_python_version()
    require_executable(
        "poetry",
        "Install Poetry first: https://python-poetry.org/docs/#installation\n"
        "Then run this script again.",
    )
    if shutil.which("psql") is None:
        print_warning(
            "`psql` is not found in PATH. The project can still run, but creating the database/user "
            "might be harder without PostgreSQL client tools."
        )

    repo_defaults = _get_default_db_env_from_repo_files()
    local_env_path = REPO_ROOT / ".env.local"
    local_env = _read_env_keys(local_env_path) if local_env_path.exists() else {}

    db_env = {
        "SQL_HOST": (args.db_host or local_env.get("SQL_HOST") or repo_defaults["SQL_HOST"]),
        "SQL_PORT": str(args.db_port or local_env.get("SQL_PORT") or repo_defaults["SQL_PORT"]),
        "SQL_DATABASE": (args.db_name or local_env.get("SQL_DATABASE") or repo_defaults["SQL_DATABASE"]),
        "SQL_USER": (args.db_user or local_env.get("SQL_USER") or repo_defaults["SQL_USER"]),
        "SQL_PASSWORD": (args.db_password or local_env.get("SQL_PASSWORD") or repo_defaults["SQL_PASSWORD"]),
    }

    print_step(2, "Ensuring .env.local")
    created = ensure_env_files(db_env)
    if created:
        for name in created:
            print_warning(f"Created {name}. Review it if you have custom settings.")
    else:
        print_success(".env.local already exists")

    env = build_subprocess_env(db_env)

    if not args.skip_install:
        print_step(3, "Installing Python dependencies (Poetry)")
        run(["poetry", "install"], env=env)
    else:
        print_step(3, "Skipping dependency installation")

    print_step(4, "Waiting for PostgreSQL")
    try:
        run(["poetry", "run", "python", "manage.py", "wait_db", f"--timeout={args.timeout}", "--interval=1"], env=env)
    except SystemExit:
        print_db_help(db_env)
        raise

    if not args.skip_migrate:
        print_step(5, "Running migrations")
        run(["poetry", "run", "python", "manage.py", "migrate", "--noinput"], env=env)
    else:
        print_step(5, "Skipping migrations")

    if not args.skip_collectstatic:
        print_step(6, "Collecting static files")
        run(["poetry", "run", "python", "manage.py", "collectstatic", "--noinput", "--clear"], env=env)
    else:
        print_step(6, "Skipping collectstatic")

    print()
    print_success("Local setup completed")
    print("Swagger UI:")
    print(f"  http://{args.host}:{args.port}/api/doc/")
    print("API base:")
    print(f"  http://{args.host}:{args.port}/api/")

    if args.no_runserver:
        return

    print_step(7, "Starting Django dev server")
    run(["poetry", "run", "python", "manage.py", "runserver", f"{args.host}:{args.port}"] , env=env)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Convenience deployment helper for TestPrj.

Features
========
* Verifies required tooling (Docker + Docker Compose).
* Ensures `.env.docker` and `.env.local` exist (creating sane defaults when missing).
* Runs `docker compose up` with clear step-by-step indication.
* Waits for critical services (db/web) to become ready.
* Prints manual instructions for alternative workflows (db-only, local Scrapy).

Usage
=====
    python deploy.py              # full stack: db + web + nginx (default)
    python deploy.py --db-only    # only the PostgreSQL container (for local Scrapy)
    python deploy.py --skip-build # reuse existing images
    python deploy.py --no-wait    # do not wait for containers to become healthy
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Literal, Sequence

REPO_ROOT = Path(__file__).resolve().parent

MANDATORY_ENV_FILES: List[tuple[str, str]] = [
    (
        ".env.docker",
        textwrap.dedent(
            """
            # Default Django settings (override as needed)
            DEBUG=True
            SECRET_KEY=django-insecure-change-me
            DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

            # Docker services
            POSTGRES_DB=mydb
            POSTGRES_USER=myuser
            POSTGRES_PASSWORD=mypassword

            SQL_ENGINE=django.db.backends.postgresql
            SQL_DATABASE=mydb
            SQL_USER=myuser
            SQL_PASSWORD=mypassword
            SQL_HOST=db
            SQL_PORT=5432

            PLAYWRIGHT_PROXY_SERVER=
            PLAYWRIGHT_PROXY_USERNAME=
            PLAYWRIGHT_PROXY_PASSWORD=

            SELENIUM_PROXY_SERVER=
            """
        ).strip()
        + "\n",
    ),
    (
        ".env.local",
        textwrap.dedent(
            """
            # Local overrides for Scrapy / host tools (not used inside Docker)
            SQL_HOST=127.0.0.1
            SQL_PORT=5434
            SQL_DATABASE=mydb
            SQL_USER=myuser
            SQL_PASSWORD=mypassword
            DJANGO_SETTINGS_MODULE=config.settings
            """
        ).strip()
        + "\n",
    ),
]

SERVICES_FULL = ["db", "web", "nginx"]
SERVICES_DB_ONLY = ["db"]
WAIT_TARGETS_FULL = ["db", "web"]
WAIT_TARGETS_DB_ONLY = ["db"]
NAMED_VOLUMES = ["postgres_data", "static_volume", "media_volume"]


def _slugify_project_name(raw: str) -> str:
    slug = re.sub(r"[^a-z0-9-]", "-", raw.lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "testprj"


DEFAULT_PROJECT_NAME = _slugify_project_name(REPO_ROOT.name)
COMPOSE_PROJECT_NAME = os.environ.get("COMPOSE_PROJECT_NAME", DEFAULT_PROJECT_NAME)


def compose_env() -> dict[str, str]:
    env = os.environ.copy()
    env["COMPOSE_PROJECT_NAME"] = COMPOSE_PROJECT_NAME
    return env


class Colors:
    """Simple ANSI color helper (disabled on non-TTY)."""

    if sys.stdout.isatty():
        HEADER = "\033[95m"
        BLUE = "\033[94m"
        CYAN = "\033[96m"
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        RED = "\033[91m"
        BOLD = "\033[1m"
        DIM = "\033[2m"
        RESET = "\033[0m"
    else:
        HEADER = BLUE = CYAN = GREEN = YELLOW = RED = BOLD = DIM = RESET = ""


def print_header() -> None:
    banner = "=" * 64
    print(f"{Colors.HEADER}{banner}{Colors.RESET}")
    print(f"{Colors.BOLD}TestPrj Deployment Helper{Colors.RESET}")
    print(banner)
    print()


def print_step(index: int, message: str) -> None:
    print(f"{Colors.BLUE}[step {index}] {message}{Colors.RESET}")


def print_success(message: str) -> None:
    print(f"{Colors.GREEN}✔ {message}{Colors.RESET}")


def print_warning(message: str) -> None:
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def print_error(message: str) -> None:
    print(f"{Colors.RED}✖ {message}{Colors.RESET}")


def ensure_repo_root() -> None:
    required_markers = ["pyproject.toml", "docker-compose.yml", "manage.py"]
    missing = [marker for marker in required_markers if not (REPO_ROOT / marker).exists()]
    if missing:
        print_error(
            "This script must be executed from the repository root (missing: " + ", ".join(missing) + ")"
        )
        sys.exit(1)


def ensure_env_files() -> List[str]:
    created: List[str] = []
    for filename, template in MANDATORY_ENV_FILES:
        path = REPO_ROOT / filename
        if path.exists():
            continue
        path.write_text(template, encoding="utf-8")
        created.append(filename)
    return created


def check_prerequisites() -> None:
    print_step(1, "Checking prerequisites")
    for binary in ("docker",):
        if shutil.which(binary) is None:
            print_error(f"Missing required executable: {binary}")
            sys.exit(1)
        result = subprocess.run([binary, "--version"], text=True, capture_output=True, check=False)
        if result.returncode == 0:
            print_success(result.stdout.strip())
        else:
            print_warning(f"Unable to read {binary} version (return code {result.returncode})")

    # Compose plugin check
    compose_check = subprocess.run(
        ["docker", "compose", "version"], text=True, capture_output=True, check=False
    )
    if compose_check.returncode != 0:
        print_error("Docker Compose V2 is required (docker compose).")
        sys.exit(1)
    print_success(compose_check.stdout.strip())


def run_compose(services: Iterable[str], build: bool) -> None:
    print_step(2, "Starting Docker Compose stack")
    cmd = ["docker", "compose", "up", "-d"]
    if build:
        cmd.insert(3, "--build")
    cmd.extend(services)
    print(f"{Colors.DIM}$ {' '.join(cmd)}{Colors.RESET}")
    result = subprocess.run(cmd, cwd=REPO_ROOT, text=True, env=compose_env())
    if result.returncode != 0:
        print_error("docker compose command failed.")
        sys.exit(result.returncode)
    print_success("docker compose up command completed")


def wait_for_services(services: Iterable[str], timeout: int = 240) -> None:
    print_step(3, "Waiting for containers to be ready")
    for service in services:
        if wait_for_service(service, timeout):
            continue
        print_warning(f"Service {service} did not become ready within {timeout} seconds")


def wait_for_service(service: str, timeout: int) -> bool:
    start = time.time()
    spinner = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    spin_index = 0
    while time.time() - start < timeout:
        container_id = subprocess.run(
            ["docker", "compose", "ps", "-q", service],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=compose_env(),
        ).stdout.strip()
        if container_id:
            inspect = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "--format",
                    "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}",
                    container_id,
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            if inspect.returncode == 0:
                status = inspect.stdout.strip().lower()
                if status in {"healthy", "running"}:
                    print_success(f"{service}: {status}")
                    return True
        print(f"\r{spinner[spin_index % len(spinner)]} waiting for {service}...", end="", flush=True)
        spin_index += 1
        time.sleep(3)
    print("")
    return False


def print_manual_instructions() -> None:
    print()
    print_step(4, "Manual command reference")
    manual = f"""
    docker compose up -d --build db web nginx
    docker compose logs -f web
    docker compose down

    # DB-only mode for local Scrapy
    docker compose up -d db

    # Local Scrapy run (PowerShell)
    Set-Location scrapy_project
    $env:DJANGO_SETTINGS_MODULE = "config.settings"
    scrapy crawl brain_bs4 -O output.json
    """
    print(textwrap.dedent(manual).strip())


def summarize(services: Iterable[str], db_only: bool) -> None:
    print()
    print_success("Деплой завершено")
    if db_only:
        print("PostgreSQL доступний на localhost:5434 (проксі з контейнера). Запускайте Scrapy локально згідно з інструкцією.")
    else:
        print("Сервіси мають бути доступні через nginx:")
        print("  • Nginx проксі:  http://localhost/")
        print("  • API:           http://localhost/api/products/")
        print("  • Swagger UI:    http://localhost/api/doc/")
        print("    (прямий Django-доступ за потреби: http://localhost:8000/)")
    print_manual_instructions()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TestPrj deployment helper")
    parser.add_argument(
        "--db-only",
        action="store_true",
        help="Only start the PostgreSQL container (for local Scrapy workflows)",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip the Docker build step and reuse existing images",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Do not wait for containers to become healthy/running",
    )
    return parser.parse_args()


@dataclass
class Conflict:
    resource_type: Literal["container", "network", "volume"]
    name: str
    note: str


def _expected_container_names(services: Sequence[str]) -> List[str]:
    names: set[str] = set()
    for service in services:
        suffix = f"{service}-1"
        names.add(f"{COMPOSE_PROJECT_NAME}-{suffix}")
        names.add(f"{COMPOSE_PROJECT_NAME}_{suffix}")
    return sorted(names)


def _expected_network_names() -> List[str]:
    return [
        f"{COMPOSE_PROJECT_NAME}_default",
        f"{COMPOSE_PROJECT_NAME}-default",
    ]


def _expected_volume_names() -> List[str]:
    names: List[str] = []
    for volume in NAMED_VOLUMES:
        names.append(f"{COMPOSE_PROJECT_NAME}_{volume}")
        names.append(f"{COMPOSE_PROJECT_NAME}-{volume}")
    return names


def _inspect_docker_resource(resource_type: str, name: str) -> tuple[bool, bool]:
    if resource_type == "container":
        cmd = ["docker", "container", "inspect", name]
    elif resource_type == "network":
        cmd = ["docker", "network", "inspect", name]
    elif resource_type == "volume":
        cmd = ["docker", "volume", "inspect", name]
    else:
        raise ValueError(f"Unsupported resource type: {resource_type}")

    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return False, False

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return True, False

    if not data:
        return False, False

    if resource_type == "container":
        labels = (data[0].get("Config") or {}).get("Labels") or {}
    else:
        labels = data[0].get("Labels") or {}
    same_project = labels.get("com.docker.compose.project") == COMPOSE_PROJECT_NAME
    return True, same_project


def detect_name_conflicts(services: Sequence[str]) -> List[Conflict]:
    conflicts: List[Conflict] = []
    for container_name in _expected_container_names(services):
        exists, same_project = _inspect_docker_resource("container", container_name)
        if exists and not same_project:
            conflicts.append(
                Conflict("container", container_name, "контейнер із таким імʼям вже існує")
            )

    for network_name in _expected_network_names():
        exists, same_project = _inspect_docker_resource("network", network_name)
        if exists and not same_project:
            conflicts.append(Conflict("network", network_name, "мережа з таким імʼям вже існує"))

    for volume_name in _expected_volume_names():
        exists, same_project = _inspect_docker_resource("volume", volume_name)
        if exists and not same_project:
            conflicts.append(Conflict("volume", volume_name, "том з таким імʼям вже існує"))
    return conflicts


def _remove_conflict(conflict: Conflict) -> bool:
    if conflict.resource_type == "container":
        cmd = ["docker", "rm", "-f", conflict.name]
    elif conflict.resource_type == "network":
        cmd = ["docker", "network", "rm", conflict.name]
    else:
        cmd = ["docker", "volume", "rm", conflict.name]

    result = subprocess.run(cmd, text=True)
    if result.returncode == 0:
        print_success(f"{conflict.resource_type} {conflict.name} видалено")
        return True
    print_error(f"Не вдалося видалити {conflict.resource_type} {conflict.name}")
    return False


def prompt_conflict_resolution(conflicts: List[Conflict]) -> None:
    print_warning("Знайдено ресурси Docker з конфліктними іменами:")
    while conflicts:
        for idx, conflict in enumerate(conflicts, start=1):
            print(
                f"  [{idx}] {conflict.resource_type}: {conflict.name} ({conflict.note})"
            )
        print("  [a] Видалити всі конфлікти")
        print("  [q] Вийти без деплою")
        try:
            choice = input("Оберіть пункт меню: ").strip().lower()
        except EOFError:
            print_error("Неможливо прочитати ввід. Припинення деплою.")
            sys.exit(1)

        if choice == "q":
            print_error("Деплой скасовано користувачем.")
            sys.exit(1)
        if choice == "a":
            remaining = []
            for conflict in conflicts:
                if not _remove_conflict(conflict):
                    remaining.append(conflict)
            conflicts = remaining
            continue
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(conflicts):
                conflict = conflicts[idx]
                if _remove_conflict(conflict):
                    conflicts.pop(idx)
                continue
        print_warning("Невірний вибір меню. Спробуйте ще раз.")


def main() -> None:
    args = parse_args()
    print_header()
    ensure_repo_root()

    created_envs = ensure_env_files()
    if created_envs:
        for env_name in created_envs:
            print_warning(f"Created missing {env_name}. Review and adjust credentials before continuing.")
    else:
        print_success("All mandatory env files present")

    check_prerequisites()

    services = SERVICES_DB_ONLY if args.db_only else SERVICES_FULL
    conflicts = detect_name_conflicts(services)
    if conflicts:
        prompt_conflict_resolution(conflicts)

    run_compose(services, build=not args.skip_build)

    if not args.no_wait:
        wait_targets = WAIT_TARGETS_DB_ONLY if args.db_only else WAIT_TARGETS_FULL
        wait_for_services(wait_targets)

    summarize(services, args.db_only)


if __name__ == "__main__":
    main()

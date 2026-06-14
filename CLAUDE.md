# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Package management uses `uv` (Python 3.13). The `Makefile` is the canonical source of commands.

- Run locally: `make run` (uvicorn with `--reload` on port 8001)
- Run all tests: `make test` (or `uv run pytest`)
- Run a single test: `uv run pytest tests/test_health.py::test_health_endpoint`
- Lint: `make lint` (`ruff check .`)
- Format: `make format` / check only: `make format-check`
- Full CI-equivalent gate: `make check-all` (ruff check + ruff format check + pyright)
- Sync deps from lockfile: `make sync` (`uv sync`)

CI (`.github/workflows/ci.yml`) runs on PRs into `develop` and enforces `ruff check`, `ruff format --check`, `pyright`, `pytest`, and a Docker build. Note CI installs via `uv pip install -r requirements.txt`, not `uv sync` — keep `requirements.txt` in sync with `pyproject.toml`.

## Architecture

FastAPI app with a strict four-layer request flow. A single endpoint (`GET /api/v1/health`) demonstrates the pattern that all new features should follow:

```
router (src/api/routers/) → service (src/services/) → repository (src/repositories/) → DB + Valkey
```

- **Routers** declare endpoints and response models only; they delegate to a service injected via `Depends`.
- **Services** hold business logic and return Pydantic schemas (`src/schemas/`). They depend on repositories, never on the DB directly.
- **Repositories** are the only layer that touches `AsyncSession` (SQLAlchemy) and the Valkey/Redis client.
- **Wiring** happens in `src/api/dependencies.py` — factory functions like `get_health_service` construct a repository from `get_db` + `get_valkey` and inject it into the service. Add new dependency factories here rather than instantiating services inline.

Routers are mounted in `src/main.py` under the `/api/v1` prefix.

### Configuration (`src/settings.py`)

`Settings` (pydantic-settings) selects the env file from the `ENVIRONMENT` variable: `dev`→`.env.dev`, `staging`→`.env.staging`, `prod`→`.env.prod`, `test`→`.env.test`.

Critical behavior: when `DOCKER_ENV != "true"`, the settings constructor rewrites `@postgres:` → `@localhost:` in `DATABASE_URL` and `valkey:` → `localhost:` in `VALKEY_URL`. This lets the same env files work both inside docker-compose (service hostnames) and on the host. Tests set `ENVIRONMENT=test` and `DOCKER_ENV=false` before importing the app.

### Database & async

- Fully async stack: SQLAlchemy 2.0 async engine + `asyncpg` (`DATABASE_URL` uses `postgresql+asyncpg://`).
- `Base`, the engine, and `get_db` (session-per-request dependency) live in `src/database.py`.
- Models inherit from `Base` and live in `src/models/`.

### Migrations (Alembic, async)

`migrations/env.py` runs migrations through the async engine and pulls the URL from `settings.DATABASE_URL`, so migrations automatically target whatever `ENVIRONMENT` is set.

Gotcha: `migrations/env.py` imports `Base` but does **not** import the model modules in `src/models/`. `--autogenerate` only detects models that have been imported into `Base.metadata`, so new models must be imported in `env.py` (or via a shared models package) or autogenerate will produce empty migrations.

Migrations run inside the docker `fastapi` container via Make targets:
- `make migrate-create msg="..."`, `make migrate-up`, `make migrate-down`, `make migrate-history`
- Environment-targeted variants: `make migrate-up-env env=staging` (sets `ENVIRONMENT` for that command)

The container `entrypoint.sh` runs `alembic upgrade head` on startup before launching uvicorn.

## Docker

`docker-compose.yml` runs `postgres` (port 5433→5432), `valkey` (6378→6379), and `fastapi` (8000). Start per-environment with the Make targets that set `ENV_FILE`/`ENVIRONMENT`:
- `make dev`, `make staging`, `make prod`
- Generic: `ENVIRONMENT=staging ENV_FILE=.env.staging docker compose up -d`

The fastapi container runs `--reload` only when `ENVIRONMENT=dev`, otherwise uvicorn with `--workers 4`.

## Conventions

- Ruff enforces Google-style docstrings (`.ruff.toml`), line length 88, double quotes. The `D` rules ignore module/class/method docstring requirements but `B008` is allowed specifically for FastAPI's `Depends()` defaults.
- `pyright` runs against `src` and `tests` (config in `pyrightconfig.json`).
- Tests are async (`asyncio_mode = auto`); patch the repository layer to isolate routes from real DB/Valkey (see `tests/test_health.py`).

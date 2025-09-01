run:
	uv run uvicorn src.main:app --reload --port 8001

test:
	uv run pytest

install:
	uv pip install requirements.txt

ps:
	docker compose ps

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs fastapi --tail=15

sync:
	uv sync

build:
	docker compose up --build -d

# Alembic migrations
migrate-create:
	docker compose exec fastapi uv run alembic revision --autogenerate -m "$(msg)"

migrate-up:
	docker compose exec fastapi uv run alembic upgrade head

migrate-down:
	docker compose exec fastapi uv run alembic downgrade -1

migrate-history:
	docker compose exec fastapi uv run alembic history

migrate-current:
	docker compose exec fastapi uv run alembic current

migrate-heads:
	docker compose exec fastapi uv run alembic heads

migrate-stamp:
	docker compose exec fastapi uv run alembic stamp $(rev)

migrate-reset:
	docker compose exec fastapi uv run alembic stamp base

# Environment-specific migrations
migrate-create-env:
	docker compose exec -e ENVIRONMENT=$(env) fastapi uv run alembic revision --autogenerate -m "$(msg)"

migrate-up-env:
	docker compose exec -e ENVIRONMENT=$(env) fastapi uv run alembic upgrade head

migrate-down-env:
	docker compose exec -e ENVIRONMENT=$(env) fastapi uv run alembic downgrade -1

migrate-history-env:
	docker compose exec -e ENVIRONMENT=$(env) fastapi uv run alembic history

# Code quality
lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

check-all:
	uv run ruff check . && uv run ruff format --check . && uv run pyright


dev:
	ENVIRONMENT=dev ENV_FILE=.env.dev docker compose up -d

staging:
	ENVIRONMENT=staging ENV_FILE=.env.staging docker compose up -d

prod:
	ENVIRONMENT=production ENV_FILE=.env.prod docker compose up -d



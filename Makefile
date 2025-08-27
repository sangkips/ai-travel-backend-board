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


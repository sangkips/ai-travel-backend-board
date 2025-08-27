# My FastAPI App

A structured FastAPI application with routers, services, repositories, and schemas.

## Setup
1. Install `uv`: `pip install uv`
2. Initialize the project: `uv init`
3. Install dependencies: `uv add fastapi uvicorn pydantic`
4. Run the app: `uv run uvicorn src.main:app --reload`

## Endpoints
- `GET /api/v1/health`: Returns the health status of the application.

## Development
- Run tests: `uv run pytest`
- Format code: `uv run black .`

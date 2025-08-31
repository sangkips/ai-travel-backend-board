# AI Travel Management App

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

## DB connectivity

```sh
psql 'postgresql://travel:travel@localhost:5432/travel'
```


## Environment-specific migrations:

### For staging
- make migrate-create-env env=staging msg="Add users table"
- make migrate-up-env env=staging
- make migrate-down-env env=staging
- make migrate-history-env env=staging

### For production
- make migrate-create-env env=prod msg="Add users table"
- make migrate-up-env env=prod
- make migrate-down-env env=prod
- make migrate-history-env env=prod

### For development
- make migrate-create-env env=dev msg="Add users table"
- make migrate-up-env env=dev

## Starting container with a specific environment

### Start with staging environment
- ENVIRONMENT=staging ENV_FILE=.env.staging docker-compose up -d

### Then run migrations (will automatically use staging)
- make migrate-up


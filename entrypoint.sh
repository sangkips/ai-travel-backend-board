#!/bin/bash
set -e

echo "Starting entrypoint script..."

# Run migrations
echo "Applying Alembic migrations for ENVIRONMENT=$ENVIRONMENT"
uv run alembic upgrade head || {
    echo "Error: Alembic migrations failed"
    exit 1
}

# Start the FastAPI app
echo "Starting FastAPI app..."
if [ "$ENVIRONMENT" = "dev" ]; then
    echo "Running in development mode with --reload"
    exec uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
else
    echo "Running in $ENVIRONMENT mode without --reload"
    exec uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
fi

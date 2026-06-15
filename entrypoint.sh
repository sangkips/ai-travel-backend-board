#!/bin/bash
set -e

echo "Starting entrypoint script..."

# Run migrations, retrying while the DB finishes coming up (crash recovery,
# slow first start, etc.). The compose healthcheck usually makes this a no-op,
# but the retry keeps a transient "not yet accepting connections" from killing
# the container.
echo "Applying Alembic migrations for ENVIRONMENT=$ENVIRONMENT"
for attempt in $(seq 1 10); do
    if uv run alembic upgrade head; then
        break
    fi
    if [ "$attempt" -eq 10 ]; then
        echo "Error: Alembic migrations failed after $attempt attempts"
        exit 1
    fi
    echo "Migration attempt $attempt failed; database not ready, retrying in 3s..."
    sleep 3
done

# Start the FastAPI app
echo "Starting FastAPI app..."
if [ "$ENVIRONMENT" = "dev" ]; then
    echo "Running in development mode with --reload"
    exec uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
else
    echo "Running in $ENVIRONMENT mode without --reload"
    exec uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
fi

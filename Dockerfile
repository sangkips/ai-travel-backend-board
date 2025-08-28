FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy pyproject.toml and uv.lock (if it exists)
COPY pyproject.toml uv.lock* ./

# Install dependencies with uv
RUN uv sync --frozen

# Copy the application code
COPY src ./src

# Expose port 8000
EXPOSE 8000

FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency manifest
COPY requirements.txt ./

# Install dependencies into the system environment
RUN uv pip install --system -r requirements.txt

# Copy the application code
COPY src ./src
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

# Run as a non-root user (best practice; satisfies Trivy DS-0002).
# uv writes its cache under $HOME, so the user needs a home directory.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose port 8000
EXPOSE 8000

# Container healthcheck (satisfies Trivy DS-0026). Uses Python's stdlib so we
# don't need curl/wget in the slim image; a non-200 response or a connection
# error raises and exits non-zero, marking the container unhealthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=4)" || exit 1

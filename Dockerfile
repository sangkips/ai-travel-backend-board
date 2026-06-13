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

# Expose port 8000
EXPOSE 8000

# Production Dockerfile for TaskForge API
FROM python:3.12-slim

# Set environment flags
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TASKFORGE_DATABASE_PATH=/app/data/taskforge.db

# Create non-root user and group
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/sh -m appuser

# Set work directory
WORKDIR /app

# Install dependencies first for build caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY taskforge/ ./taskforge/

# Prepare persistent data directory with permissions for appuser
RUN mkdir -p /app/data && chown -R appuser:appgroup /app && chmod 700 /app/data

# Switch to unprivileged user
USER appuser

# Expose FastAPI port
EXPOSE 8000

# Container healthcheck using standard library urllib
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')" || exit 1

# Launch uvicorn bound to 0.0.0.0:8000 with reverse proxy header support
CMD ["uvicorn", "taskforge.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]

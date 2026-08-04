# Stage 1: Build dependency wheels
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ ./requirements/

RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements/production.txt

# Stage 2: Minimal runtime image
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Install runtime system packages (curl for health check, libpq5 for DB connection)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python packages from builder
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir /wheels/* && \
    rm -rf /wheels

# Create non-root user and group
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/bash -m appuser

# Copy application source code
COPY . .

# Run collectstatic with dummy environment variables during the build process
RUN mkdir -p staticfiles media logs && \
    SECRET_KEY=dummy-build-key DB_ENGINE=django.db.backends.sqlite3 DB_NAME=dummy_db python manage.py collectstatic --noinput

# Ensure correct ownership of application files
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# Expose Django port
EXPOSE 8000

# Container healthcheck using Django's health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health/ || exit 1

# Default command will start the application via Gunicorn
CMD ["gunicorn", "--config", "deployment/docker/gunicorn.conf.py", "jewellery_saas.wsgi:application"]

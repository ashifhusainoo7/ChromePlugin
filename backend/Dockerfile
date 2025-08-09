# Multi-stage build for production optimization
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ffmpeg \
    git \
    libpq-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Install Chrome for Selenium
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list && \
    apt-get update && apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# Development stage
FROM base as development

# Install development dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install pytest pytest-asyncio pytest-cov black isort flake8 mypy

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs uploads /tmp/chrome-user-data && \
    chown -R appuser:appuser /app logs uploads /tmp/chrome-user-data

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production

# Install only production dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-dev -r requirements.txt && \
    pip install gunicorn[gevent]

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p logs uploads /tmp/chrome-user-data && \
    chown -R appuser:appuser /app logs uploads /tmp/chrome-user-data

# Remove unnecessary files for production
RUN find . -type f -name "*.pyc" -delete && \
    find . -type d -name "__pycache__" -delete && \
    rm -rf tests/ .pytest_cache/ .git/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

USER appuser

EXPOSE 8000

# Production command with Gunicorn
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--keepalive", "2", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]

# Final stage selector
FROM ${BUILD_ENV:-production} as final
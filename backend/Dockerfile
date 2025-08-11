# ===== Base image (light) =====
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Minimal deps for local dev
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app

# ===== Development (super fast) =====
FROM base AS development

COPY requirements.txt requirements.txt
# Use pip cache for faster rebuilds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install pytest pytest-asyncio pytest-cov black isort flake8 mypy

# Copy source code
COPY . .

# Create dirs
RUN mkdir -p logs uploads && \
    chown -R appuser:appuser /app logs uploads

USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ===== Production (heavy) =====
FROM python:3.11-slim AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install heavy system deps here ONLY for prod
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libpq-dev \
    wget \
    curl \
    git \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list && \
    apt-get update && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app

COPY requirements.txt requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn[gevent]

COPY . .

RUN mkdir -p logs uploads /tmp/chrome-user-data && \
    chown -R appuser:appuser /app logs uploads /tmp/chrome-user-data

# Cleanup
RUN find . -type f -name "*.pyc" -delete && \
    find . -type d -name "__pycache__" -delete && \
    rm -rf tests/ .pytest_cache/ .git/

USER appuser
EXPOSE 8000

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

# ===== Final stage selector =====
FROM ${BUILD_ENV:-development} AS final

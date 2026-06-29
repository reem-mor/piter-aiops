# syntax=docker/dockerfile:1.7

FROM node:22-alpine AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash app
WORKDIR /home/app

COPY --chown=app:app requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app app ./app
COPY --chown=app:app action_groups ./action_groups
COPY --chown=app:app wsgi.py ./wsgi.py
# Local-mode assets: knowledge base for offline RAG + operational datasets.
COPY --chown=app:app knowledge_base ./knowledge_base
COPY --chown=app:app data ./data
COPY --from=frontend-build --chown=app:app /build/app/static/spa ./app/static/spa

RUN mkdir -p /home/app/var && chown app:app /home/app/var

USER app

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS http://localhost:8080/health || exit 1

# Persist chat + session memory across container restarts (mount at /home/app/var).

# Single worker + threads: follow-up requests should hit the same process when possible;
# session state is persisted under var/ for restart survival.
CMD ["gunicorn", \
     "--workers", "1", \
     "--threads", "4", \
     "--bind", "0.0.0.0:8080", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "wsgi:app"]

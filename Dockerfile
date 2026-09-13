# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Web: build the Next.js static export (served by FastAPI at /ui).
# ---------------------------------------------------------------------------
FROM node:22-alpine AS web

WORKDIR /web

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Builder: install runtime dependencies with uv into a project virtualenv.
# `uv.lock` is intentionally not committed (it may embed a private PyPI index
# URL), so `uv sync` runs without `--frozen` and resolves at build time.
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_NO_CACHE=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN uv sync --no-dev

# ---------------------------------------------------------------------------
# Runtime: slim, non-root, no build tooling.
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd --system app && \
    useradd --system --gid app --create-home --home-dir /home/app app

WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app src ./src
COPY --from=web --chown=app:app /web/out ./web/out

USER app

EXPOSE 9009

CMD ["nine-bars"]

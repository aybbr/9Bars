# 9Bars — Makefile
# =============================================================================
# Uses the Rancher Desktop `docker` CLI for local container work.
# The app listens on port 9009 by default (override with PORT=/NINE_BARS_PORT).

CONTAINER ?= docker
IMAGE ?= nine-bars
PORT ?= 9009

.PHONY: install lint format typecheck lint-imports test check run dev build docker-run demo build-web

install:
	uv sync

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .

typecheck:
	uv run mypy src

lint-imports:
	uv run lint-imports

test:
	uv run pytest

check: lint typecheck lint-imports test

run:
	uv run nine-bars

dev:
	uv run uvicorn --factory nine_bars.main:create_app --host 0.0.0.0 --port $(PORT) --reload

build:
	$(CONTAINER) build -t $(IMAGE) .

docker-run:
	$(CONTAINER) run --rm -p $(PORT):$(PORT) -e PORT=$(PORT) $(IMAGE)

build-web:
	cd web && npm ci && npm run build

demo:
	./scripts/demo.sh

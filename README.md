# 9Bars

Nine bars of pressure. None on you ☕️

9Bars is a [Strands Agents](https://strandsagents.com/) assistant for home
espresso enthusiasts with Gaggiuino- or GaggiMate-controlled machines. It turns
the full dial-in workflow into an agentic loop: research a coffee, draft and
validate an extraction profile, get your approval, upload it, review the real
shot, collect taste feedback, and recommend exactly one next change.

> Built for the [Agents for Humans Hackathon](https://agentsforhumans.devpost.com/).

## Prerequisites

- **uv** (Python package + environment manager) — https://docs.astral.sh/uv/
- **Python 3.13** (managed automatically by uv via `.python-version`)
- **Rancher Desktop** (or any Docker CLI) for container builds

## Setup

```bash
uv sync
```

This creates the virtual environment and installs all dependencies, including
the `nine-bars` console script.

## Run locally

```bash
make run
```

The API serves `GET /healthz` on `http://localhost:9009`. Once the web UI is
built (see below), the app is served at `http://localhost:9009/ui`.

For development with auto-reload:

```bash
make dev
```

## Web UI

The UI is a Next.js static export (`web/`) served by FastAPI at `/ui`.

```bash
make build-web    # npm ci + next build → web/out
```

The chat has two modes:

- **live** — set `DEEPSEEK_API_KEY` and the chat runs the real Strands agent.
- **demo** — with no key, the chat replays a scripted dial-in arc against the
  fixture shots, fully offline.

### Run the demo

```bash
make demo         # builds the UI, resets demo data, serves on :9009
```

Then open http://localhost:9009/ui and click **Run the full demo**. The arc:
research → profile draft → approve → shot 1 → one change → shot 2 → comparison.

End-to-end smoke tests (offline, no API key required):

```bash
cd web && npm run test:e2e
```

## Quality gates

```bash
make lint          # ruff check + format --check
make typecheck     # mypy --strict
make lint-imports  # import-linter (domain-purity contract)
make test          # pytest
make check         # all of the above
```

## Run in Docker (Rancher Desktop)

```bash
make build        # docker build -t nine-bars .
make docker-run   # docker run -p 9009:9009 nine-bars
```

Verify:

```bash
curl http://localhost:9009/healthz   # {"status":"ok"}
```

The image runs as a non-root `app` user and listens on the `PORT` environment
variable (default `9009`).

## Deploy to Railway

The repository is Railway-ready via a root `Dockerfile` plus Infrastructure as
Code (`.railway/railway.ts`):

1. Install and authenticate the Railway CLI: `railway login`.
2. Link the directory to a project/environment: `railway link`.
3. Preview the plan: `railway config plan`.
4. Apply: `railway config apply`.

Railway auto-detects the `Dockerfile`, injects a `PORT` variable that the app
honours, and gates deployments on the `/healthz` healthcheck. See
[Railway Infrastructure as Code](https://docs.railway.com/infrastructure-as-code)
for details.

## Project structure

```text
src/nine_bars/
├── main.py       # FastAPI app factory + entrypoint
├── config.py     # pydantic-settings configuration
├── domain/       # pure models, physics, rules, decisions
├── application/  # use cases / services
├── adapters/     # ports (Protocols) + implementations
├── agent/        # the Strands agent
├── web.py        # web-UI routes (chat SSE, activity, telemetry, demo)
└── fixtures/     # replay fixtures
web/              # Next.js static export (served at /ui)
tests/            # mirrors src/
```

## License

[MIT](LICENSE)

# pygrab

Lightweight observability backend for logs and distributed traces.

Accepts logs via HTTP push, collects from Docker containers, receives OpenTelemetry (OTLP) traces, and provides a Loki-compatible query API. Uses ClickHouse for storage. Comes with a built-in terminal UI.

## Features

- **Log ingestion** — HTTP push API, Loki-compatible push, Docker container log collection.
- **Distributed tracing** — OTLP trace ingestion with span correlation and tree rendering.
- **Loki-compatible API** — query logs with `{service="my-app", level="error"}` selectors.
- **Docker collector** — streams stdout/stderr from configured containers, auto-detects log levels, manages attachments dynamically.
- **Terminal UI** — browse logs and traces, filter by service/environment, search, live tail.
- **ClickHouse storage** — high-performance analytical storage for log entries and traces.

## Project Structure

```text
pygrab/
├── app/                        # Python FastAPI Backend
│   ├── api/                    # Routers and endpoints
│   │   ├── dependencies.py
│   │   └── v1/                 # Endpoints separated for TUI and Loki
│   │       ├── ingest.py
│   │       ├── loki.py
│   │       └── traces.py
│   ├── application/            # Services and core logic
│   │   ├── collector/          # Docker collector worker and parsers
│   │   ├── logs/               # Log pipeline and memory buffering
│   │   ├── query/              # LogQL selectors parser
│   │   ├── traces/             # OTLP converters and trace services
│   │   └── utils/              # Time formatters and TUI payload mappers
│   ├── domain/                 # Models, enums, and domain rules
│   └── infrastructure/         # ClickHouse connections pool & repositories
├── db/                         # ClickHouse database migrations
├── tui/                        # Autonomous Rust TUI client (Ratatui)
│   ├── Cargo.toml              # Dependencies config
│   └── src/                    # UI code, client modules, and state engines
└── docker-compose.yml          # Infrastructure orchestration (API, ClickHouse, Redis)
```

## Configuration

Copy `.env.example` to `.env` and adjust the variables:

```env
LOG_LEVEL=info
LISTEN_HOST=0.0.0.0
LISTEN_PORT=8000

# ClickHouse Configuration
CLICKHOUSE_DB=pygrab_db
CLICKHOUSE_USER=pygrab_user
CLICKHOUSE_PASSWORD=your_secure_password
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123

# Docker Collector Configuration
DOCKER_ENABLED=True
DOCKER_SOCKET=unix:///var/run/docker.sock
DOCKER_CONTAINERS='[{"name": "fastapi-app", "service": "backend", "environment": "production"}, {"name": "nginx", "service": "nginx", "environment": "production"}]'
```

## Docker Collector Metadata

When `DOCKER_ENABLED=True`, the application attaches to the Docker daemon socket and appends metadata labels to each ingested line:

| Label | Source |
|--------|--------|
| service | Explicit mapping from configuration, falling back to container name |
| environment | Context environment string from configuration |
| container_name | Raw name parsed from Docker event |
| container_id | Truncated unique container hash identifier |
| stream | Source descriptor (`stdout` or `stderr`) |

## Quick Start

### 1. Boot Infrastructure

Ensure Docker daemon is running locally. Spin up the background ingestion pipelines, analytical DB, and workers:

```bash
docker compose up --build -d
```

The backend instance listens on port `8000` by default.

### 2. Launch Terminal UI

The TUI dashboard runs autonomously and is placed under the `tui/` directory.

From the root directory of the project, execute:

```bash
cargo run --manifest-path tui/Cargo.toml -- --server http://localhost:8000
```

Or change the working directory directly:

```bash
cd tui && cargo run -- --server http://localhost:8000
```

## API Reference

### Log Ingestion

#### Native HTTP JSON Push (Array of LogEntry)

```bash
curl -X POST http://localhost:8000/v1/logs \
  -H 'Content-Type: application/json' \
  -d '[{"timestamp":1719830400000000000,"level":"INFO","message":"Server started","labels":{"service":"core"}}]'
```

#### Loki-compatible Push Endpoint

```bash
curl -X POST http://localhost:8000/pygrab/api/v1/push \
  -H 'Content-Type: application/json' \
  -d '{"streams":[{"stream":{"service":"proxy"},"values":[["1719830400000000000","GET /index.html 200"]]}]}'
```

### OTLP Distributed Tracing

Push OpenTelemetry JSON spans directly:

```bash
curl -X POST http://localhost:8000/api/otlp/v1/traces \
  -H 'Content-Type: application/json' \
  -d @traces.json
```

### Queries & Metadata

List registered label names:

```bash
curl http://localhost:8000/pygrab/api/v1/labels
```

Fetch distinct values for a given label:

```bash
curl http://localhost:8000/pygrab/api/v1/label/service/values
```

Internal query endpoints utilized by the TUI client:

```bash
curl 'http://localhost:8000/api/logs?limit=200&offset=0'
curl 'http://localhost:8000/api/traces?limit=100'
```

## TUI Keybindings

| Key | Action |
|-----|--------|
| Tab | Toggle layout context between Logs and Traces views |
| j / k | Navigate viewport row selection downwards / upwards |
| h / l | Swap element focus between side panel tree and primary data table |
| Enter | Toggle target label filtering scope / Explode runtime span execution hierarchy |
| / | Focus search context console overlay for raw message matching |
| 1 - 6 | Toggle visualization display rules for specific log severities (TRACE..FATAL) |
| L | Lock viewport tail orientation to real-time incoming records (Live Tail) |
| s | Reverse sort order constraints index |
| q | Terminate session and exit to terminal shell |

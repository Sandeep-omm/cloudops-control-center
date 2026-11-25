# CloudOps Control Center

A local-first data processing platform that demonstrates an API, PostgreSQL-backed worker queue, containerized services, CI, and application monitoring. The full demo runs on your computer; an AWS deployment design is planned as a separate learning layer.

## Start locally

Prerequisites: Docker Desktop with its Linux container engine running, and Docker Compose v2 or later.

```powershell
docker compose up --build
```

Open these local pages:

- Dashboard: http://localhost:8080
- API documentation: http://localhost:8080/docs
- Grafana: http://localhost:3001 (local demo login: `admin` / `admin-local-only`)
- Prometheus: http://localhost:9091

Select **Run sample data** to queue the included sample in the UI, or upload a UTF-8 CSV smaller than 5 MB. The processor counts valid and rejected rows, totals an optional `amount` column, and groups an optional `category` column. An amount that cannot be parsed rejects that row. Other CSVs are accepted and counted without those optional summaries.

Stop services with `Ctrl+C`, or from another PowerShell window run:

```powershell
docker compose down
```

This keeps the database and Grafana volumes. To reset the demo database and monitoring state, run `docker compose down --volumes`; that permanently removes those local Docker volumes.

## Services

| Service | Purpose | Local port |
|---|---|---:|
| FastAPI | Job API, dashboard, health, and API metrics | 8080 |
| PostgreSQL | Durable job state and summaries | 5432 (container network only) |
| Worker | Claims and processes queued CSV jobs | Metrics 8001 (container network only) |
| Prometheus | Scrapes API and worker metrics | 9091 |
| Grafana | Provisioned operations dashboard | 3001 |

The worker claims jobs with PostgreSQL row locks (`SKIP LOCKED`), so two workers can safely share the queue. Uploads are size-limited and named with generated IDs; original user paths are never used for storage paths. The API and worker run as a non-root container user.

## Useful commands

```powershell
docker compose ps
docker compose logs -f api worker
docker compose config
```

Health endpoints: `/health/live` and `/health/ready`. Job endpoints start at `/api/v1/jobs`. Prometheus metrics are at `/metrics` on the API and worker.

## Database migrations and tests

Compose applies versioned Alembic migrations before starting the API and worker. CI applies migrations to PostgreSQL, runs the automated suite, lints and compiles the Python code, and builds the container image.

Run the suite in a disposable container with an isolated SQLite database:

```powershell
docker compose --profile test run --build --rm test
```

For host development, install the development dependencies and run tests with an isolated SQLite database:

```powershell
python -m pip install -e ".[dev]"
python -m pytest
```

## Configuration

Compose has local-only defaults so the first run is quick. Before sharing the machine or exposing ports beyond localhost, create a `.env` from `.env.example` and set unique local credentials. Never put cloud credentials or real customer data in this repository. The demo uses local ports and has no authentication, so keep it on a trusted development machine.

## Repository map

```text
app/                 FastAPI routes, persistence, metrics, and dashboard
worker/              PostgreSQL queue consumer and CSV processing
monitoring/          Prometheus scrape config and provisioned Grafana dashboard
tests/               API and worker behavior tests
migrations/          Alembic environment and versioned schema revisions
infra/terraform/     Optional AWS networking, data, storage, and IAM example
docs/                Architecture, security, and operations notes
.github/workflows/   Test, lint, compile, migration, and container validation
```

## Roadmap

- [x] Local API, database, worker, dashboard, and observability stack
- [x] Container health checks and non-root application container
- [x] CI static checks and image build
- [x] Automated test suite and database migrations
- [x] Terraform AWS example with disabled-by-default resources and a cost guide
- [ ] Optional Kubernetes manifests and local cluster walkthrough
- [ ] Screenshots and short project demo recording

The AWS and Kubernetes items are documentation and infrastructure extensions; they are not needed to run the local product. Free-tier eligibility and pricing vary, so check current provider pricing before creating cloud resources.

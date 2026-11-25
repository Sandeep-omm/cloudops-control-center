# Local operations

## Start and stop

Run `docker compose up --build`. Stop with Ctrl+C, then use `docker compose down` if needed. Database and dashboard state remain in named volumes. `docker compose down --volumes` removes them permanently.

The `migrate` service runs `alembic upgrade head` once before the API and worker start. To apply later migrations to an already running stack, use `docker compose run --rm migrate`.

## Inspect

- `docker compose ps` shows container state and health.
- `docker compose logs -f api worker` follows application logs.
- `http://localhost:8080/health/live` checks API process liveness.
- `http://localhost:8080/health/ready` checks API-to-database readiness.
- `http://localhost:9091/targets` shows Prometheus scrape health.
- Grafana is available at `http://localhost:3001`; the `CloudOps` folder is provisioned automatically.

## Current limitations

The worker has no automatic retry or stale-job recovery yet. The API has no auth and is intended for localhost. Uploads are removed after processing; only the summary remains. Schema changes are managed with Alembic migrations.

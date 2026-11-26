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

## AWS demo host

The optional AWS stack is operated through Systems Manager Session Manager. Start one SSM port-forwarding session for the API (remote port `8080` to local port `8080`) and a separate session for Grafana (remote port `3001` to local port `3301`). Keep each terminal open while using its local browser URL. Retrieve the Grafana admin password from the SecureString parameter named by `terraform output -raw grafana_password_parameter`; do not paste the password into logs or chat. The EC2 host has no inbound rules, and RDS remains private.

Use `sudo docker compose --project-directory /opt/cloudops-control-center --file /opt/cloudops-control-center/compose.aws.yaml ps` in an SSM shell to inspect container status. Check `logs --tail=80 <service>` for a specific failing service, and redact URLs or credentials before sharing logs. AWS resources incur charges while active; review the AWS billing console and the Terraform cost notes before leaving the demo running.

## Current limitations

The worker has no automatic retry or stale-job recovery yet. The API has no auth and should remain local or reachable only through the AWS Session Manager tunnel. Inputs are removed after processing; a JSON result is kept in local storage or in the S3 `results/` prefix and expires according to the bucket lifecycle policy. Schema changes are managed with Alembic migrations. The local Kubernetes runbook is in [kubernetes.md](kubernetes.md).

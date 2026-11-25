# Architecture

## Local request and job flow

1. The dashboard posts a CSV file to the FastAPI service.
2. A one-shot Alembic migration service applies versioned schema changes. The API checks the extension, UTF-8 encoding, and a 5 MB upload cap, stores the bytes under a generated UUID, and inserts a `queued` row.
3. A worker claims one queued row in a short transaction using `FOR UPDATE SKIP LOCKED`, then reads and processes the shared-volume file.
4. The worker writes the result summary and terminal state to PostgreSQL, then removes the temporary upload.
5. The browser polls the API; Prometheus scrapes metrics from both application processes and Grafana visualizes them.

## Persistence

PostgreSQL is the source of truth for job state. Compose volumes keep the database and Grafana state across restarts. Uploaded input files live only while jobs are queued or running; the result summary is stored as JSON in PostgreSQL.

## Failure behavior

An invalid amount rejects that row. File-level processing errors mark the job failed with a bounded error message. The initial version does not retry failed jobs or recover a worker that is terminated mid-job; adding bounded retries and a stale-job lease is a planned reliability improvement.

## Optional AWS mapping

The Terraform example defines a two-AZ VPC, private database subnets, private PostgreSQL RDS, versioned S3 storage, and a prefix-scoped EC2 instance profile. Resource creation is disabled by default. The app itself is not deployed to AWS and its database is not migrated to RDS. No cloud resources are needed by the local demo.

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

## AWS demo deployment

Terraform can create a two-AZ VPC, private PostgreSQL RDS, a versioned private S3 bucket, and a single EC2 host. The host runs the API, worker, Prometheus, and Grafana containers; it has no inbound security-group rules and is accessed through Systems Manager port forwarding. RDS accepts PostgreSQL only from the EC2 security group.

In local mode, the API and worker share a persistent Docker volume for input and JSON result files. In AWS mode, the API writes uploads under the S3 `incoming/` prefix, and the worker downloads, processes, and removes each input. It writes the job result as JSON under `results/`; the API serves that object from the result endpoint. S3 access uses the EC2 instance profile and is scoped to those prefixes. Local mode requires no AWS resources. Terraform resource creation is disabled by default, and AWS usage can incur charges.

The optional Kubernetes deployment in `deploy/kubernetes/` runs the same API and worker with PostgreSQL and the existing Prometheus/Grafana dashboard on a local cluster. It uses persistent volumes and a staged migration Job; it does not require AWS.

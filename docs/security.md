# Security notes

- This is a local development demo with no authentication. Keep it on a trusted machine and do not expose it publicly.
- Compose defaults are demo credentials, not production secrets. Use private `.env` files with unique values; `.env` and `.env.*` files are ignored by Git and Docker build contexts. `.env.example` is the safe committed template.
- Uploaded names are reduced to a display basename; the stored path uses a generated UUID. AWS input and result keys are generated from the job ID, encrypted at rest, and restricted to the `incoming/` and `results/` prefixes by the EC2 role.
- Upload size is capped, CSV parsing is UTF-8 only, and database values are persisted through SQLAlchemy.
- App containers run as a non-root user. PostgreSQL is not published to the host.
- Do not upload personal, customer, or otherwise sensitive data.
- The AWS demo keeps the API and monitoring ports on EC2 loopback and uses Session Manager tunnels; it has no application authentication. Production work would require authentication/authorization, managed secret rotation, TLS, stricter network policy, migration management, backup/restore, and cloud-specific IAM review.
- The AWS API and worker containers use the EC2 instance profile for scoped S3 access. IMDSv2 remains required; its response hop limit is `2` so bridge-network containers can receive the token response. Only run trusted containers on this instance, and keep the instance role and security group restricted.

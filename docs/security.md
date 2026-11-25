# Security notes

- This is a local development demo with no authentication. Keep it on a trusted machine and do not expose it publicly.
- Compose defaults are demo credentials, not production secrets. Use a private `.env` with unique values for local sharing; `.env` is ignored by Git.
- Uploaded names are reduced to a display basename; the stored path uses a generated UUID.
- Upload size is capped, CSV parsing is UTF-8 only, and database values are persisted through SQLAlchemy.
- App containers run as a non-root user. PostgreSQL is not published to the host.
- Do not upload personal, customer, or otherwise sensitive data.
- Production work would require authentication/authorization, managed secret storage, TLS, stricter network policy, migration management, backup/restore, and cloud-specific IAM review.

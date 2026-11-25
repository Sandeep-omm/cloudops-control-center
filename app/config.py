import os
from pathlib import Path

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://cloudops_app:change-me-local-only@localhost:5432/cloudops",
)
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
MAX_ROWS = int(os.getenv("MAX_ROWS", "100000"))

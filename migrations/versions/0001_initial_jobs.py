"""Create initial jobs table.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "jobs" not in inspector.get_table_names():
        op.create_table(
            "jobs",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("input_path", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("processed_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("rejected_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
        )
    else:
        existing_columns = {column["name"] for column in inspector.get_columns("jobs")}
        required_columns = {
            "id", "filename", "input_path", "status", "created_at", "started_at",
            "completed_at", "attempts", "processed_rows", "rejected_rows", "summary", "error",
        }
        missing_columns = required_columns - existing_columns
        if missing_columns:
            raise RuntimeError(
                "Cannot adopt existing jobs table; missing columns: "
                f"{sorted(missing_columns)}"
            )

    existing_indexes = {index["name"] for index in sa.inspect(bind).get_indexes("jobs")}
    if "ix_jobs_status" not in existing_indexes:
        op.create_index("ix_jobs_status", "jobs", ["status"])
    if "ix_jobs_created_at" not in existing_indexes:
        op.create_index("ix_jobs_created_at", "jobs", ["created_at"])


def downgrade() -> None:
    # Preserve job data: this baseline may have adopted a table from the earlier local demo.
    pass

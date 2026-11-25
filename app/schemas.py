from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    status: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    attempts: int
    processed_rows: int
    rejected_rows: int
    summary: dict | None
    error: str | None

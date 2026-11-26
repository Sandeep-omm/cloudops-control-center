import csv
import json
import logging
import tempfile
import time
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

from prometheus_client import Counter as PromCounter
from prometheus_client import Gauge, Histogram, start_http_server

from app.config import DATA_DIR, MAX_ROWS
from app.db import SessionLocal
from app.models import Job, utcnow
from app.storage import get_storage

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("cloudops.worker")
JOBS = PromCounter("jobs_processed_total", "Jobs completed by outcome", ["outcome"])
JOB_DURATION = Histogram("job_processing_duration_seconds", "Job processing time")
WORKER_UP = Gauge("worker_up", "Whether the job worker is running")


def claim_job() -> Job | None:
    with SessionLocal() as session:
        job = (
            session.query(Job)
            .filter(Job.status == "queued")
            .order_by(Job.created_at)
            .with_for_update(skip_locked=True)
            .first()
        )
        if job is None:
            return None
        job.status = "running"
        job.started_at = utcnow()
        job.attempts += 1
        session.commit()
        return job


def process_csv(path: Path) -> tuple[int, int, dict]:
    processed = 0
    rejected = 0
    total_amount = Decimal("0")
    categories: Counter[str] = Counter()
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames:
            raise ValueError("CSV must include a header row")
        headers = {header.strip().lower() for header in reader.fieldnames if header}
        if not headers:
            raise ValueError("CSV header row is empty")
        has_amount = "amount" in headers
        has_category = "category" in headers
        for row_number, row in enumerate(reader, start=1):
            if row_number > MAX_ROWS:
                raise ValueError(f"CSV exceeds the {MAX_ROWS:,} row limit")
            if not any(value and value.strip() for value in row.values()):
                rejected += 1
                continue
            if has_amount:
                try:
                    amount_field = next(
                        key for key in row if key and key.strip().lower() == "amount"
                    )
                    amount = Decimal((row.get(amount_field) or "").strip())
                    if not amount.is_finite():
                        raise InvalidOperation
                    total_amount += amount
                except (InvalidOperation, StopIteration):
                    rejected += 1
                    continue
            if has_category:
                category_field = next(
                    key for key in row if key and key.strip().lower() == "category"
                )
                category = (row.get(category_field) or "Uncategorized").strip() or "Uncategorized"
                categories[category] += 1
            processed += 1

    summary = {
        "columns": reader.fieldnames,
        "total_amount": str(total_amount.quantize(Decimal("0.01"))),
        "categories": dict(categories.most_common(10)),
    }
    return processed, rejected, summary


def run_once() -> bool:
    job = claim_job()
    if job is None:
        return False
    started = time.perf_counter()
    outcome = "failed"
    storage = get_storage()
    temporary_path = None
    try:
        contents = storage.get_input(job.input_path)
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".csv", dir=DATA_DIR, delete=False
        ) as temporary_file:
            temporary_file.write(contents)
            temporary_path = Path(temporary_file.name)
        processed, rejected, summary = process_csv(temporary_path)
        result = {
            "job_id": job.id,
            "filename": job.filename,
            "processed_rows": processed,
            "rejected_rows": rejected,
            "summary": summary,
        }
        storage.put_result(job.id, result)
        with SessionLocal() as session:
            current = session.get(Job, job.id)
            if current:
                current.status = "succeeded"
                current.processed_rows = processed
                current.rejected_rows = rejected
                current.summary = summary
                current.completed_at = utcnow()
                current.error = None
                session.commit()
        outcome = "succeeded"
        logger.info(
            json.dumps(
                {
                    "event": "job_completed",
                    "job_id": job.id,
                    "processed_rows": processed,
                    "rejected_rows": rejected,
                }
            )
        )
    except Exception as exc:
        with SessionLocal() as session:
            current = session.get(Job, job.id)
            if current:
                current.status = "failed"
                current.error = str(exc)[:500]
                current.completed_at = utcnow()
                session.commit()
        logger.exception("%s", json.dumps({"event": "job_failed", "job_id": job.id}))
    finally:
        JOBS.labels(outcome).inc()
        JOB_DURATION.observe(time.perf_counter() - started)
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        try:
            storage.delete_input(job.input_path)
        except Exception:
            logger.exception(
                "%s",
                json.dumps({"event": "job_input_cleanup_failed", "job_id": job.id}),
            )
    return True


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    start_http_server(8001)
    WORKER_UP.set(1)
    logger.info('{"event":"worker_started"}')
    while True:
        if not run_once():
            time.sleep(2)


if __name__ == "__main__":
    main()

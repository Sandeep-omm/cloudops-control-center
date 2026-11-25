import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import desc, func, select, text
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import DATA_DIR, MAX_UPLOAD_BYTES
from app.db import SessionLocal, engine
from app.metrics import HTTP_DURATION, HTTP_REQUESTS, metrics_response
from app.models import Job
from app.schemas import JobRead

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("cloudops.api")


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        path = request.url.path if request.url.path.startswith(("/api/", "/health")) else "/other"
        HTTP_REQUESTS.labels(request.method, path, str(response.status_code)).inc()
        HTTP_DURATION.labels(request.method, path).observe(time.perf_counter() - started)
        return response


@asynccontextmanager
async def lifespan(_: FastAPI):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info('{"event":"api_started"}')
    yield


app = FastAPI(title="CloudOps Control Center", version="0.1.0", lifespan=lifespan)
app.add_middleware(RequestMetricsMiddleware)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health/live", include_in_schema=False)
def liveness():
    return {"status": "alive"}


@app.get("/health/ready", include_in_schema=False)
def readiness():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ready", "database": "available"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc


@app.get("/metrics", include_in_schema=False)
def metrics():
    return metrics_response()


@app.get("/api/v1/jobs", response_model=list[JobRead])
def list_jobs(
    status: Annotated[str | None, Query(pattern="^(queued|running|succeeded|failed)$")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    with SessionLocal() as session:
        query = select(Job).order_by(desc(Job.created_at)).limit(limit).offset(offset)
        if status:
            query = query.where(Job.status == status)
        return session.scalars(query).all()


@app.get("/api/v1/jobs/summary")
def job_summary():
    with SessionLocal() as session:
        counts = dict(session.execute(select(Job.status, func.count()).group_by(Job.status)).all())
    statuses = ("queued", "running", "succeeded", "failed")
    return {status: counts.get(status, 0) for status in statuses}


@app.post("/api/v1/jobs", response_model=JobRead, status_code=201)
async def create_job(file: Annotated[UploadFile, File()]):
    if not file.filename or Path(file.filename).suffix.lower() != ".csv":
        raise HTTPException(status_code=415, detail="Upload a .csv file")

    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded file is empty")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_BYTES} bytes")
    try:
        contents.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must use UTF-8 encoding") from exc

    job_id = str(uuid4())
    input_path = DATA_DIR / f"{job_id}.csv"
    input_path.write_bytes(contents)
    job = Job(id=job_id, filename=Path(file.filename).name[:255], input_path=str(input_path))
    try:
        with SessionLocal() as session:
            session.add(job)
            session.commit()
            session.refresh(job)
            return job
    except Exception:
        input_path.unlink(missing_ok=True)
        logger.exception('{"event":"job_submission_failed","job_id":"%s"}', job_id)
        raise HTTPException(status_code=503, detail="Could not queue the job") from None


@app.get("/api/v1/jobs/{job_id}", response_model=JobRead)
def get_job(job_id: str):
    with SessionLocal() as session:
        job = session.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return job


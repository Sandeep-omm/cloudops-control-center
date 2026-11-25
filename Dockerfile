FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir .
COPY app ./app
COPY worker ./worker
COPY scripts ./scripts
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
RUN useradd --create-home --uid 10001 appuser && mkdir -p /data && chown -R appuser:appuser /app /data
USER appuser
EXPOSE 8000 8001

FROM base AS test
USER root
COPY tests ./tests
RUN pip install --no-cache-dir ".[dev]"
USER appuser
CMD ["pytest", "-q"]

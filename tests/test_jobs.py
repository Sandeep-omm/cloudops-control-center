from pathlib import Path

SAMPLE_CSV = (
    "order_id,customer_id,order_date,amount,category\n"
    "1001,C-10,2026-10-01,125.50,hardware\n"
    "1002,C-11,2026-10-02,49.99,software\n"
    "1003,C-10,2026-10-03,210.00,hardware\n"
    "1004,C-12,2026-10-04,not-a-number,services\n"
    "1005,C-14,2026-10-05,84.25,services\n"
)


def test_sample_job_completes_end_to_end(client):
    from worker.main import run_once

    submitted = client.post(
        "/api/v1/jobs",
        files={"file": ("orders.csv", SAMPLE_CSV, "text/csv")},
    )
    assert submitted.status_code == 201
    created = submitted.json()
    assert created["status"] == "queued"
    assert Path(created["filename"]).name == "orders.csv"

    assert run_once() is True

    result = client.get(f"/api/v1/jobs/{created['id']}")
    assert result.status_code == 200
    job = result.json()
    assert job["status"] == "succeeded"
    assert job["processed_rows"] == 4
    assert job["rejected_rows"] == 1
    assert job["summary"]["total_amount"] == "469.74"
    assert job["summary"]["categories"] == {"hardware": 2, "software": 1, "services": 1}
    result = client.get(f"/api/v1/jobs/{created['id']}/result")
    assert result.status_code == 200
    assert result.json()["summary"] == job["summary"]
    assert client.get("/api/v1/jobs/summary").json() == {
        "queued": 0,
        "running": 0,
        "succeeded": 1,
        "failed": 0,
    }


def test_upload_rejects_non_csv(client):
    response = client.post("/api/v1/jobs", files={"file": ("orders.txt", "data", "text/plain")})
    assert response.status_code == 415
    assert response.json()["detail"] == "Upload a .csv file"


def test_upload_rejects_empty_file(client):
    response = client.post("/api/v1/jobs", files={"file": ("empty.csv", b"", "text/csv")})
    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded file is empty"


def test_job_lookup_returns_404_for_unknown_id(client):
    response = client.get("/api/v1/jobs/unknown-job")
    assert response.status_code == 404


def test_result_is_unavailable_until_job_succeeds(client):
    submitted = client.post(
        "/api/v1/jobs",
        files={"file": ("orders.csv", SAMPLE_CSV, "text/csv")},
    )
    response = client.get(f"/api/v1/jobs/{submitted.json()['id']}/result")
    assert response.status_code == 409


def test_request_metrics_use_route_template_not_job_id(client):
    from app.metrics import metrics_response

    assert client.get("/api/v1/jobs/first-id").status_code == 404
    assert client.get("/api/v1/jobs/second-id").status_code == 404

    metrics = metrics_response().body.decode()
    assert 'path="/api/v1/jobs/{job_id}"' in metrics
    assert 'path="/api/v1/jobs/first-id"' not in metrics
    assert 'path="/api/v1/jobs/second-id"' not in metrics


def test_processor_requires_a_header(tmp_path):
    from worker.main import process_csv

    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")
    try:
        process_csv(path)
    except ValueError as exc:
        assert str(exc) == "CSV must include a header row"
    else:
        raise AssertionError("Expected a missing-header validation error")


def test_worker_marks_invalid_csv_as_failed(client):
    from worker.main import run_once

    response = client.post(
        "/api/v1/jobs",
        files={"file": ("empty-header.csv", "\n", "text/csv")},
    )
    assert response.status_code == 201
    job_id = response.json()["id"]

    assert run_once() is True
    result = client.get(f"/api/v1/jobs/{job_id}")
    assert result.status_code == 200
    assert result.json()["status"] == "failed"
    assert result.json()["error"] == "CSV must include a header row"

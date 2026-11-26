import json
from io import BytesIO
from pathlib import Path

import boto3
from botocore.response import StreamingBody
from botocore.stub import Stubber

from app.storage import LocalObjectStorage, S3ObjectStorage


def test_local_storage_persists_input_and_result(tmp_path):
    storage = LocalObjectStorage(tmp_path)

    location = storage.put_input("job-123", b"amount\n2.50\n")
    assert Path(location).read_bytes() == b"amount\n2.50\n"
    assert storage.get_input(location) == b"amount\n2.50\n"

    expected = {"job_id": "job-123", "processed_rows": 1}
    storage.put_result("job-123", expected)
    assert storage.get_result("job-123") == expected

    storage.delete_input(location)
    assert not Path(location).exists()


def test_s3_storage_uploads_reads_deletes_and_stores_result():
    client = boto3.client(
        "s3",
        region_name="ap-southeast-2",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    storage = S3ObjectStorage("demo-bucket", "ap-southeast-2", client=client)
    result = {"job_id": "job-123", "processed_rows": 1}
    result_bytes = json.dumps(result, sort_keys=True).encode("utf-8")
    input_bytes = b"amount\n2.50\n"

    with Stubber(client) as stubber:
        stubber.add_response(
            "put_object",
            {"ETag": '"input-etag"'},
            {
                "Bucket": "demo-bucket",
                "Key": "incoming/job-123.csv",
                "Body": input_bytes,
                "ContentType": "text/csv",
                "ServerSideEncryption": "AES256",
            },
        )
        stubber.add_response(
            "get_object",
            {
                "Body": StreamingBody(BytesIO(input_bytes), len(input_bytes)),
                "ContentLength": len(input_bytes),
            },
            {"Bucket": "demo-bucket", "Key": "incoming/job-123.csv"},
        )
        stubber.add_response(
            "delete_object",
            {},
            {"Bucket": "demo-bucket", "Key": "incoming/job-123.csv"},
        )
        stubber.add_response(
            "put_object",
            {"ETag": '"result-etag"'},
            {
                "Bucket": "demo-bucket",
                "Key": "results/job-123.json",
                "Body": result_bytes,
                "ContentType": "application/json",
                "ServerSideEncryption": "AES256",
            },
        )
        stubber.add_response(
            "get_object",
            {
                "Body": StreamingBody(BytesIO(result_bytes), len(result_bytes)),
                "ContentLength": len(result_bytes),
            },
            {"Bucket": "demo-bucket", "Key": "results/job-123.json"},
        )

        location = storage.put_input("job-123", input_bytes)
        assert location == "s3://demo-bucket/incoming/job-123.csv"
        assert storage.get_input(location) == input_bytes
        storage.delete_input(location)
        assert storage.put_result("job-123", result) == "s3://demo-bucket/results/job-123.json"
        assert storage.get_result("job-123") == result

        stubber.assert_no_pending_responses()


def test_s3_storage_rejects_object_outside_expected_prefix():
    client = boto3.client(
        "s3",
        region_name="ap-southeast-2",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    storage = S3ObjectStorage("demo-bucket", "ap-southeast-2", client=client)

    try:
        storage.get_input("s3://demo-bucket/results/job-123.json")
    except ValueError as exc:
        assert "allowed prefix" in str(exc)
    else:
        raise AssertionError("Expected S3 key-prefix validation to fail")


def test_s3_storage_returns_none_when_result_does_not_exist():
    client = boto3.client(
        "s3",
        region_name="ap-southeast-2",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    storage = S3ObjectStorage("demo-bucket", "ap-southeast-2", client=client)

    with Stubber(client) as stubber:
        stubber.add_client_error(
            "get_object",
            service_error_code="NoSuchKey",
            http_status_code=404,
            expected_params={"Bucket": "demo-bucket", "Key": "results/job-123.json"},
        )
        assert storage.get_result("job-123") is None
        stubber.assert_no_pending_responses()

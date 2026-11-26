import json
import os
from functools import lru_cache
from pathlib import Path

import boto3
from botocore.config import Config

from app.config import DATA_DIR


class LocalObjectStorage:
    def __init__(self, root: Path = DATA_DIR):
        self.root = root

    def put_input(self, job_id: str, contents: bytes) -> str:
        path = self.root / f"{job_id}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
        return str(path)

    def get_input(self, location: str) -> bytes:
        return Path(location).read_bytes()

    def delete_input(self, location: str) -> None:
        Path(location).unlink(missing_ok=True)

    def put_result(self, job_id: str, result: dict) -> str:
        path = self.root / "results" / f"{job_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, sort_keys=True), encoding="utf-8")
        return str(path)

    def get_result(self, job_id: str) -> dict | None:
        path = self.root / "results" / f"{job_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))


class S3ObjectStorage:
    def __init__(self, bucket: str, region: str, client=None):
        if not bucket:
            raise ValueError("S3_BUCKET is required when OBJECT_STORAGE_BACKEND=s3")
        if not region:
            raise ValueError("AWS_REGION is required when OBJECT_STORAGE_BACKEND=s3")
        self.bucket = bucket
        self.client = client or boto3.client(
            "s3",
            region_name=region,
            config=Config(
                retries={"total_max_attempts": 3, "mode": "standard"},
                connect_timeout=5,
                read_timeout=15,
            ),
        )

    @staticmethod
    def _input_key(job_id: str) -> str:
        return f"incoming/{job_id}.csv"

    @staticmethod
    def _result_key(job_id: str) -> str:
        return f"results/{job_id}.json"

    def put_input(self, job_id: str, contents: bytes) -> str:
        key = self._input_key(job_id)
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=contents,
            ContentType="text/csv",
            ServerSideEncryption="AES256",
        )
        return f"s3://{self.bucket}/{key}"

    def get_input(self, location: str) -> bytes:
        key = self._key_from_location(location, "incoming/")
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        with response["Body"] as body:
            return body.read()

    def delete_input(self, location: str) -> None:
        key = self._key_from_location(location, "incoming/")
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def put_result(self, job_id: str, result: dict) -> str:
        key = self._result_key(job_id)
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(result, sort_keys=True).encode("utf-8"),
            ContentType="application/json",
            ServerSideEncryption="AES256",
        )
        return f"s3://{self.bucket}/{key}"

    def get_result(self, job_id: str) -> dict | None:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=self._result_key(job_id))
        except self.client.exceptions.NoSuchKey:
            return None
        with response["Body"] as body:
            return json.loads(body.read())

    def _key_from_location(self, location: str, required_prefix: str) -> str:
        expected = f"s3://{self.bucket}/"
        if not location.startswith(expected):
            raise ValueError("Stored object location does not match the configured bucket")
        key = location[len(expected) :]
        if not key.startswith(required_prefix) or "/" in key[len(required_prefix) :]:
            raise ValueError("Stored object location is outside the allowed prefix")
        return key


@lru_cache(maxsize=1)
def get_storage():
    backend = os.getenv("OBJECT_STORAGE_BACKEND", "local").lower()
    if backend == "local":
        return LocalObjectStorage()
    if backend == "s3":
        return S3ObjectStorage(
            bucket=os.getenv("S3_BUCKET", ""),
            region=os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "")),
        )
    raise ValueError("OBJECT_STORAGE_BACKEND must be 'local' or 's3'")

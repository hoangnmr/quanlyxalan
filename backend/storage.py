"""Attachment storage and scanner boundaries."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol


class ObjectStorage(Protocol):
    backend_name: str
    def put_quarantined(self, object_key: str, content: bytes) -> str: ...


class LocalQuarantineStorage:
    backend_name = "LOCAL_QUARANTINE"

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def put_quarantined(self, object_key: str, content: bytes) -> str:
        target = (self.root / object_key).resolve()
        if self.root not in target.parents:
            raise ValueError("Object key nằm ngoài quarantine root.")
        target.write_bytes(content)
        return object_key


class MinioQuarantineStorage:
    """Lazy MinIO adapter; only active when explicitly configured."""

    backend_name = "MINIO_S3_QUARANTINE"

    def __init__(self, endpoint: str, bucket: str, access_key: str, secret_key: str, secure: bool):
        if not all((endpoint, bucket, access_key, secret_key)):
            raise ValueError("MinIO requires endpoint, bucket and credential environment variables.")
        try:
            from minio import Minio
        except ImportError as exc:
            raise RuntimeError("MinIO adapter requires the optional 'minio' package.") from exc
        self.bucket = bucket
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)

    def put_quarantined(self, object_key: str, content: bytes) -> str:
        from io import BytesIO

        key = f"quarantine/{object_key}"
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)
        self.client.put_object(self.bucket, key, BytesIO(content), len(content))
        return key


def get_attachment_storage(local_root: Path) -> ObjectStorage:
    mode = os.getenv("OBJECT_STORAGE_MODE", "LOCAL").strip().upper()
    if mode != "MINIO":
        return LocalQuarantineStorage(local_root)
    return MinioQuarantineStorage(
        endpoint=os.getenv("MINIO_ENDPOINT", "").strip(),
        bucket=os.getenv("MINIO_BUCKET", "").strip(),
        access_key=os.getenv("MINIO_ACCESS_KEY", "").strip(),
        secret_key=os.getenv("MINIO_SECRET_KEY", "").strip(),
        secure=os.getenv("MINIO_SECURE", "true").strip().lower() == "true",
    )


class AttachmentScanner(Protocol):
    def scan(self, object_key: str) -> str: ...


class ScannerNotConfigured:
    """Fail-closed scanner used until Defender/ClamAV is configured."""

    def scan(self, object_key: str) -> str:
        return "QUARANTINED"

"""MinIO (S3-compatible) evidence client for QAZen runs.

Creates the qa-runs bucket on first use (see infra/docker-compose.yml note).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env", override=False)


def _settings() -> dict[str, str | bool]:
    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    secure = os.getenv("MINIO_SECURE", "false").lower() in ("1", "true", "yes")
    return {
        "endpoint": endpoint,
        "access_key": os.getenv("MINIO_ACCESS_KEY", "qazen"),
        "secret_key": os.getenv("MINIO_SECRET_KEY", "qazen_local_dev"),
        "bucket": os.getenv("MINIO_BUCKET", "qa-runs"),
        "secure": secure,
    }


def _client():
    from minio import Minio  # lazy so mock-only paths never need the package wired

    cfg = _settings()
    return Minio(
        str(cfg["endpoint"]),
        access_key=str(cfg["access_key"]),
        secret_key=str(cfg["secret_key"]),
        secure=bool(cfg["secure"]),
    ), str(cfg["bucket"])


def ensure_bucket() -> str:
    client, bucket = _client()
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    return bucket


def upload_file(
    local_path: Path | str,
    *,
    run_id: str,
    correlation_id: str,
    object_name: Optional[str] = None,
    content_type: str = "application/octet-stream",
) -> str:
    """Upload a local file; return s3-style URI s3://bucket/run_id/correlation_id/..."""
    path = Path(local_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))

    client, bucket = _client()
    ensure_bucket()
    key_tail = object_name or path.name
    object_key = f"{run_id}/{correlation_id}/{key_tail}".replace("\\", "/")
    client.fput_object(bucket, object_key, str(path), content_type=content_type)
    return f"s3://{bucket}/{object_key}"


def upload_directory(
    local_dir: Path | str,
    *,
    run_id: str,
    correlation_id: str,
) -> list[dict[str, str]]:
    """Upload all files under local_dir; return [{relative_path, storage_uri}, ...]."""
    root = Path(local_dir)
    if not root.is_dir():
        return []
    uploaded: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        uri = upload_file(
            path,
            run_id=run_id,
            correlation_id=correlation_id,
            object_name=rel,
        )
        uploaded.append({"relative_path": rel, "storage_uri": uri})
    return uploaded

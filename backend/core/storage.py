import logging
from pathlib import Path

import boto3
from botocore.config import Config as BotoConfig

from core.config import settings
from core.crypto import decrypt_file, encrypt_file

logger = logging.getLogger(__name__)


class LocalStorage:
    def __init__(self, base_path: str = "/app/uploads"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, key: str, data: bytes) -> str:
        path = self.base_path / key
        path.parent.mkdir(parents=True, exist_ok=True)
        encrypted = encrypt_file(data)
        path.write_bytes(encrypted)
        return str(path)

    def load(self, key: str) -> bytes | None:
        path = self.base_path / key
        if not path.exists():
            return None
        encrypted = path.read_bytes()
        try:
            return decrypt_file(encrypted)
        except Exception:
            logger.exception("Failed to decrypt file %s", key)
            return None

    def delete(self, key: str) -> bool:
        path = self.base_path / key
        if path.exists():
            path.unlink()
            return True
        return False

    def exists(self, key: str) -> bool:
        return (self.base_path / key).exists()


class S3Storage:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint,
            aws_access_key_id=settings.r2_access_key,
            aws_secret_access_key=settings.r2_secret_key,
            config=BotoConfig(signature_version="s3v4"),
        )
        self.bucket = "retromind-uploads"

    def _ensure_bucket(self):
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            self.client.create_bucket(Bucket=self.bucket)

    def save(self, key: str, data: bytes) -> str:
        self._ensure_bucket()
        encrypted = encrypt_file(data)
        self.client.put_object(Bucket=self.bucket, Key=key, Body=encrypted)
        return f"s3://{self.bucket}/{key}"

    def load(self, key: str) -> bytes | None:
        try:
            resp = self.client.get_object(Bucket=self.bucket, Key=key)
            encrypted = resp["Body"].read()
            return decrypt_file(encrypted)
        except self.client.exceptions.NoSuchKey:
            return None
        except Exception:
            logger.exception("Failed to decrypt S3 file %s", key)
            return None

    def delete(self, key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False


def get_storage() -> LocalStorage | S3Storage:
    if settings.r2_endpoint and settings.r2_access_key and settings.r2_secret_key:
        return S3Storage()
    return LocalStorage(settings.upload_dir)

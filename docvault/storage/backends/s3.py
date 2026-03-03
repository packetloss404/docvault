"""S3-compatible storage backend (works with MinIO and AWS S3)."""

import io
from typing import BinaryIO

from django.conf import settings

from .base import StorageBackend


class S3StorageBackend(StorageBackend):
    """Store files in S3-compatible object storage (AWS S3, MinIO)."""

    def __init__(self):
        import boto3

        self.bucket_name = settings.S3_BUCKET_NAME
        session_kwargs = {
            "aws_access_key_id": settings.S3_ACCESS_KEY,
            "aws_secret_access_key": settings.S3_SECRET_KEY,
            "region_name": settings.S3_REGION,
        }
        client_kwargs = {}
        if settings.S3_ENDPOINT_URL:
            client_kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL

        session = boto3.session.Session(**session_kwargs)
        self.client = session.client("s3", **client_kwargs)
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create the S3 bucket if it doesn't exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except self.client.exceptions.ClientError:
            self.client.create_bucket(Bucket=self.bucket_name)

    def _key(self, name: str) -> str:
        """Prefix all keys with 'documents/'."""
        return f"documents/{name}" if not name.startswith("documents/") else name

    def save(self, name: str, content: BinaryIO) -> str:
        key = self._key(name)
        self.client.upload_fileobj(content, self.bucket_name, key)
        return name

    def open(self, name: str) -> BinaryIO:
        key = self._key(name)
        buf = io.BytesIO()
        self.client.download_fileobj(self.bucket_name, key, buf)
        buf.seek(0)
        return buf

    def delete(self, name: str) -> None:
        key = self._key(name)
        self.client.delete_object(Bucket=self.bucket_name, Key=key)

    def exists(self, name: str) -> bool:
        key = self._key(name)
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except self.client.exceptions.ClientError:
            return False

    def url(self, name: str) -> str:
        key = self._key(name)
        if settings.S3_ENDPOINT_URL:
            return f"{settings.S3_ENDPOINT_URL}/{self.bucket_name}/{key}"
        return f"https://{self.bucket_name}.s3.{settings.S3_REGION}.amazonaws.com/{key}"

    def size(self, name: str) -> int:
        key = self._key(name)
        resp = self.client.head_object(Bucket=self.bucket_name, Key=key)
        return resp["ContentLength"]

    def list_files(self, prefix: str = "") -> list[str]:
        full_prefix = self._key(prefix) if prefix else "documents/"
        paginator = self.client.get_paginator("list_objects_v2")
        files = []
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=full_prefix):
            for obj in page.get("Contents", []):
                # Strip the 'documents/' prefix to match local backend convention
                key = obj["Key"]
                if key.startswith("documents/"):
                    key = key[len("documents/"):]
                files.append(key)
        return files

"""S3-compatible object storage backend.

Covers AWS S3, Backblaze B2, MinIO and Cloudflare R2 through one client. The
differences between them are small but fatal if unhandled, so each provider has
a preset rather than expecting operators to discover the flags themselves:

* **Backblaze B2** — boto3 >= 1.36 sends `x-amz-sdk-checksum-algorithm` and
  `x-amz-checksum-crc32` on every upload by default. B2's S3 API rejects those
  headers outright ("Unsupported header ... received for this API call"), so
  checksum calculation has to be dialled back to `when_required`.
  See https://github.com/jschneier/django-storages/issues/1498
* **MinIO** — typically deployed on a bare host or container name, where
  virtual-host-style addressing (`bucket.host`) does not resolve. Needs
  path-style.
* **R2** — same checksum problem as B2, and it ignores regions.
"""

import io
import logging
from typing import BinaryIO

from django.conf import settings

from .base import StorageBackend

logger = logging.getLogger(__name__)

# Per-provider defaults. Anything explicitly set in settings still wins.
PROVIDER_PRESETS = {
    "s3": {"addressing_style": "auto", "disable_checksums": False},
    "b2": {"addressing_style": "virtual", "disable_checksums": True},
    "minio": {"addressing_style": "path", "disable_checksums": True},
    "r2": {"addressing_style": "virtual", "disable_checksums": True},
}


def _preset(provider: str) -> dict:
    return PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS["s3"])


def build_client_config(provider: str, addressing_style=None, disable_checksums=None):
    """Build a botocore Config appropriate for the provider.

    The checksum options only exist on botocore >= 1.36; on older versions the
    defaults are already what we want, so their absence is not an error.
    """
    from botocore.config import Config

    preset = _preset(provider)
    style = addressing_style or preset["addressing_style"]
    disable = preset["disable_checksums"] if disable_checksums is None else disable_checksums

    kwargs = {
        "signature_version": "s3v4",
        "s3": {"addressing_style": style},
        "retries": {"max_attempts": 5, "mode": "standard"},
    }
    if disable:
        kwargs["request_checksum_calculation"] = "when_required"
        kwargs["response_checksum_validation"] = "when_required"

    try:
        return Config(**kwargs)
    except TypeError:
        # botocore too old for the checksum knobs; it also predates the
        # behaviour that made them necessary.
        kwargs.pop("request_checksum_calculation", None)
        kwargs.pop("response_checksum_validation", None)
        return Config(**kwargs)


class S3StorageBackend(StorageBackend):
    """Store documents in S3-compatible object storage."""

    def __init__(self, config=None):
        import boto3

        cfg = config or {}

        def setting(key, default=None):
            """Prefer an explicit config mapping, else fall back to settings.

            Only `None` means "not specified" — an empty string is a real value
            (no key prefix, no custom endpoint) and must not fall through.
            """
            if key in cfg and cfg[key] is not None:
                return cfg[key]
            return getattr(settings, key, default)

        self.provider = (setting("S3_PROVIDER", "s3") or "s3").lower()
        self.bucket_name = setting("S3_BUCKET_NAME", "docvault")
        prefix = setting("S3_PREFIX", "documents")
        self.prefix = ("" if prefix is None else str(prefix)).strip("/")
        endpoint = setting("S3_ENDPOINT_URL", "") or None
        region = setting("S3_REGION", "us-east-1")

        client_config = build_client_config(
            self.provider,
            addressing_style=setting("S3_ADDRESSING_STYLE", None),
            disable_checksums=setting("S3_DISABLE_CHECKSUMS", None),
        )

        session = boto3.session.Session(
            aws_access_key_id=setting("S3_ACCESS_KEY", ""),
            aws_secret_access_key=setting("S3_SECRET_KEY", ""),
            region_name=region,
        )
        self.client = session.client(
            "s3", endpoint_url=endpoint, config=client_config
        )

        if setting("S3_AUTO_CREATE_BUCKET", False):
            self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create the bucket if it is genuinely absent.

        Not on by default: production credentials are often scoped to a single
        existing bucket, in which case `head_bucket` returns 403 rather than
        404 and creating is neither possible nor wanted.
        """
        from botocore.exceptions import ClientError

        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            return
        except ClientError as exc:
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status != 404:
                logger.warning(
                    "Cannot verify bucket %s (HTTP %s); assuming it exists.",
                    self.bucket_name,
                    status,
                )
                return

        try:
            self.client.create_bucket(Bucket=self.bucket_name)
            logger.info("Created bucket %s", self.bucket_name)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                raise

    def _key(self, name: str) -> str:
        """Namespace every object under the configured prefix."""
        if not self.prefix:
            return name
        return name if name.startswith(f"{self.prefix}/") else f"{self.prefix}/{name}"

    def _strip(self, key: str) -> str:
        marker = f"{self.prefix}/"
        return key[len(marker):] if self.prefix and key.startswith(marker) else key

    def save(self, name: str, content: BinaryIO) -> str:
        self.client.upload_fileobj(content, self.bucket_name, self._key(name))
        return name

    def open(self, name: str) -> BinaryIO:
        buf = io.BytesIO()
        self.client.download_fileobj(self.bucket_name, self._key(name), buf)
        buf.seek(0)
        return buf

    def delete(self, name: str) -> None:
        self.client.delete_object(Bucket=self.bucket_name, Key=self._key(name))

    def exists(self, name: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.client.head_object(Bucket=self.bucket_name, Key=self._key(name))
            return True
        except ClientError:
            return False

    def url(self, name: str) -> str:
        """A direct URL to the object.

        Documents are normally streamed through the API so permissions are
        enforced; this is for the cases that legitimately want a direct link.
        """
        key = self._key(name)
        endpoint = getattr(settings, "S3_ENDPOINT_URL", "")
        if endpoint:
            return f"{endpoint.rstrip('/')}/{self.bucket_name}/{key}"
        region = getattr(settings, "S3_REGION", "us-east-1")
        return f"https://{self.bucket_name}.s3.{region}.amazonaws.com/{key}"

    def presigned_url(self, name: str, expires_in: int = 3600) -> str:
        """Time-limited URL, so a direct link cannot be shared indefinitely."""
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": self._key(name)},
            ExpiresIn=expires_in,
        )

    def size(self, name: str) -> int:
        resp = self.client.head_object(Bucket=self.bucket_name, Key=self._key(name))
        return resp["ContentLength"]

    def list_files(self, prefix: str = "") -> list[str]:
        full_prefix = self._key(prefix) if prefix else f"{self.prefix}/" if self.prefix else ""
        paginator = self.client.get_paginator("list_objects_v2")
        files = []
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=full_prefix):
            for obj in page.get("Contents", []):
                files.append(self._strip(obj["Key"]))
        return files

    def check(self) -> dict:
        """Round-trip probe used by the admin "test connection" action."""
        import uuid

        from botocore.exceptions import BotoCoreError, ClientError

        probe = f".docvault-connection-test-{uuid.uuid4().hex}"
        try:
            self.client.put_object(
                Bucket=self.bucket_name, Key=self._key(probe), Body=b"ok"
            )
            self.client.head_object(Bucket=self.bucket_name, Key=self._key(probe))
            self.client.delete_object(Bucket=self.bucket_name, Key=self._key(probe))
        except (ClientError, BotoCoreError) as exc:
            return {"ok": False, "error": str(exc)}
        return {
            "ok": True,
            "provider": self.provider,
            "bucket": self.bucket_name,
            "prefix": self.prefix,
        }

"""Views for the storage module."""

import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class DedupStatsView(APIView):
    """
    GET endpoint returning content-addressable storage deduplication statistics.

    Admin-only access.
    """

    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from storage.utils import get_storage_backend

        from .backends.content_addressed import ContentAddressedStorageBackend

        backend = get_storage_backend()

        # If the backend is wrapped in content-addressed storage, use it directly.
        # Otherwise, wrap the current backend.
        if isinstance(backend, ContentAddressedStorageBackend):
            cas = backend
        else:
            cas = ContentAddressedStorageBackend(underlying_backend=backend)

        stats = cas.get_dedup_stats()
        return Response(stats)


class VerifyIntegrityView(APIView):
    """
    POST endpoint that triggers an async storage integrity verification.

    Admin-only access. Returns immediately with a task confirmation.
    """

    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        from .tasks import verify_storage_integrity

        verify_storage_integrity.delay()
        return Response(
            {"status": "integrity_check_queued"},
            status=status.HTTP_202_ACCEPTED,
        )


class StorageConfigView(APIView):
    """GET/PATCH the storage configuration (admin only).

    Changing the backend does **not** move existing documents. Anything already
    written to the previous backend stays there and stops resolving, so the
    response carries an explicit warning rather than leaving callers to find out.
    """

    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from .models import StorageConfig
        from .serializers import StorageConfigSerializer

        config = StorageConfig.load()
        data = StorageConfigSerializer(config).data
        data["effective_backend"] = _effective_backend()
        data["source"] = "database" if config.enabled else "environment"
        return Response(data)

    def patch(self, request):
        from .models import StorageConfig
        from .serializers import StorageConfigSerializer

        config = StorageConfig.load()
        previous_backend = config.backend
        serializer = StorageConfigSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user if request.user.is_authenticated else None)

        data = serializer.data
        data["effective_backend"] = _effective_backend()
        if serializer.instance.backend != previous_backend:
            data["warning"] = (
                f"Backend changed from '{previous_backend}' to "
                f"'{serializer.instance.backend}'. Existing documents are not "
                "migrated and will not resolve until they are moved."
            )
        return Response(data)


class StorageConnectionTestView(APIView):
    """POST a candidate configuration and round-trip a probe object.

    Accepts the same fields as the config endpoint so credentials can be
    verified before they are saved. With an empty body it tests what is
    currently stored.
    """

    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        from .backends.s3 import S3StorageBackend
        from .models import StorageConfig
        from .serializers import StorageConnectionTestSerializer
        from .utils import S3_COMPATIBLE

        if request.data:
            serializer = StorageConnectionTestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            payload = serializer.validated_data
            backend_name = payload["backend"]
            stored = StorageConfig.load()
            # Let an omitted secret fall back to the stored one, so the UI can
            # re-test without asking the operator to retype it.
            secret = payload.get("secret_key") or stored.secret_key
            config = {
                "S3_PROVIDER": backend_name,
                "S3_BUCKET_NAME": payload.get("bucket_name") or stored.bucket_name,
                "S3_ENDPOINT_URL": payload.get("endpoint_url") or stored.endpoint_url,
                "S3_REGION": payload.get("region") or stored.region,
                "S3_ACCESS_KEY": payload.get("access_key") or stored.access_key,
                "S3_SECRET_KEY": secret,
                "S3_PREFIX": payload.get("prefix") or stored.prefix,
                "S3_ADDRESSING_STYLE": payload.get("addressing_style") or None,
                "S3_DISABLE_CHECKSUMS": payload.get("disable_checksums"),
            }
        else:
            stored = StorageConfig.load()
            backend_name = stored.backend
            config = stored.as_backend_config()

        if backend_name not in S3_COMPATIBLE:
            return Response(
                {"ok": True, "provider": backend_name,
                 "detail": "Local filesystem storage needs no connection test."}
            )

        try:
            result = S3StorageBackend(config=config).check()
        except Exception as exc:  # noqa: BLE001 - surface any client error verbatim
            logger.warning("Storage connection test failed: %s", exc)
            return Response({"ok": False, "error": str(exc)})

        http_status = status.HTTP_200_OK if result.get("ok") else status.HTTP_400_BAD_REQUEST
        return Response(result, status=http_status)


class StorageBackendsView(APIView):
    """GET the available backends and which one is serving requests."""

    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from .models import StorageConfig

        effective = _effective_backend()
        backends = [
            {
                "id": value,
                "label": label,
                "object_storage": value != "local",
                "requires_endpoint": value in {"b2", "minio", "r2"},
                "active": value == effective,
            }
            for value, label in StorageConfig.Backend.choices
        ]
        return Response({"backends": backends, "effective": effective})


def _effective_backend() -> str:
    """The backend actually in use, database override included."""
    from .utils import _resolve_config

    backend, _ = _resolve_config()
    return backend

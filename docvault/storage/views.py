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

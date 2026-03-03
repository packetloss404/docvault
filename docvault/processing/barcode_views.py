"""API views for barcode and ASN management."""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.models import Document

from .barcode_utils import get_barcode_settings, get_next_asn


class NextAsnView(APIView):
    """GET /api/v1/asn/next/ — Returns the next available ASN."""

    def get(self, request):
        next_asn = get_next_asn()
        return Response({"next_asn": next_asn})


class BulkAsnAssignView(APIView):
    """POST /api/v1/asn/bulk-assign/ — Assign ASNs to documents without one."""

    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        document_ids = request.data.get("document_ids", [])
        if not document_ids:
            return Response(
                {"error": "document_ids is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assigned = []
        next_asn = get_next_asn()

        for doc_id in document_ids:
            try:
                doc = Document.objects.get(pk=doc_id)
            except Document.DoesNotExist:
                continue

            if doc.archive_serial_number is not None:
                continue  # Skip docs that already have an ASN

            doc.archive_serial_number = next_asn
            doc.save(update_fields=["archive_serial_number"])
            assigned.append({"document_id": doc.id, "asn": next_asn})
            next_asn += 1

        return Response({"assigned": assigned, "count": len(assigned)})


class BarcodeConfigView(APIView):
    """GET /api/v1/barcode/config/ — Returns current barcode configuration."""

    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        conf = get_barcode_settings()
        return Response(conf)

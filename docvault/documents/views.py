"""Views for the documents module."""

import difflib
import hashlib
import io
import logging
import tempfile
import zipfile
from pathlib import Path

from django.http import FileResponse, Http404, HttpResponse, StreamingHttpResponse
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from security.permissions import (
    DocVaultObjectPermissions,
    IsAdminOrReadOnly,
    get_objects_for_user_with_ownership,
)

from .filters import DocumentFilterSet
from .models import Document, DocumentFile, DocumentType, DocumentVersion
from .serializers import (
    DocumentListSerializer,
    DocumentSerializer,
    DocumentTypeSerializer,
    DocumentVersionSerializer,
)

logger = logging.getLogger(__name__)


class DocumentViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for Documents.

    Supports filtering, searching, ordering, and soft delete.
    Permissions: authenticated users can create; owners and users with
    guardian object permissions can read/update/delete.
    """

    permission_classes = [permissions.IsAuthenticated, DocVaultObjectPermissions]
    filterset_class = DocumentFilterSet
    search_fields = ["title", "content", "original_filename"]
    ordering_fields = [
        "title", "created", "added",
        "archive_serial_number", "created_at",
    ]
    ordering = ["-created"]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Document.objects.all()
        return get_objects_for_user_with_ownership(
            user, "documents.view_document", Document.objects.all(),
        )

    def get_serializer_class(self):
        if self.action == "list":
            return DocumentListSerializer
        return DocumentSerializer

    def perform_create(self, serializer):
        serializer.save(
            owner=self.request.user,
            created_by=self.request.user,
        )

    def _check_legal_hold(self, instance):
        """Raise 409 if document is under legal hold and user lacks override."""
        if instance.is_held and not self.request.user.has_perm(
            "legal_hold.override_hold"
        ):
            from rest_framework.exceptions import APIException

            class LegalHoldConflict(APIException):
                status_code = 409
                default_detail = (
                    "This document is under legal hold. "
                    "Modifications and deletion are restricted."
                )
                default_code = "legal_hold_conflict"

            raise LegalHoldConflict()

    def perform_update(self, serializer):
        self._check_legal_hold(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        """Soft delete instead of hard delete."""
        self._check_legal_hold(instance)
        instance.soft_delete()

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        """Restore a soft-deleted document."""
        doc = Document.all_objects.get(pk=pk)
        doc.restore()
        return Response(DocumentSerializer(doc).data)

    @action(detail=False, methods=["get"])
    def deleted(self, request):
        """List soft-deleted documents (trash)."""
        user = request.user
        if user.is_superuser:
            qs = Document.all_objects.dead()
        else:
            qs = Document.all_objects.dead().filter(owner=user)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = DocumentListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = DocumentListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="preview")
    def preview(self, request, pk=None):
        """Serve the document thumbnail with ETag caching."""
        doc = self.get_object()

        if not doc.thumbnail_path:
            raise Http404("No thumbnail available for this document.")

        from storage.utils import get_storage_backend
        backend = get_storage_backend()

        if not backend.exists(doc.thumbnail_path):
            raise Http404("Thumbnail file not found.")

        # ETag-based caching
        etag = hashlib.md5(doc.thumbnail_path.encode()).hexdigest()
        if request.META.get("HTTP_IF_NONE_MATCH") == etag:
            return HttpResponse(status=304)

        file_handle = backend.open(doc.thumbnail_path)
        response = FileResponse(file_handle, content_type="image/webp")
        response["ETag"] = etag
        response["Cache-Control"] = "public, max-age=86400"
        return response

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        """Download the document file (original or archive version)."""
        doc = self.get_object()
        version = request.query_params.get("version", "original")

        from storage.utils import get_storage_backend
        backend = get_storage_backend()

        if version == "archive" and doc.archive_filename:
            storage_name = doc.archive_filename
            content_type = "application/pdf"
            download_name = Path(doc.original_filename).stem + ".pdf"
        elif doc.filename:
            storage_name = doc.filename
            content_type = doc.mime_type or "application/octet-stream"
            download_name = doc.original_filename
        else:
            raise Http404("No file available for this document.")

        if not backend.exists(storage_name):
            raise Http404("File not found in storage.")

        # Checksum verification
        expected_checksum = (
            doc.archive_checksum if version == "archive" else doc.checksum
        )
        if expected_checksum:
            file_handle = backend.open(storage_name)
            sha256 = hashlib.sha256()
            for chunk in iter(lambda: file_handle.read(65536), b""):
                sha256.update(chunk)
            actual_checksum = sha256.hexdigest()
            file_handle.close()

            if actual_checksum != expected_checksum:
                logger.error(
                    "Checksum mismatch for document %s (%s): expected %s, got %s",
                    doc.pk, version, expected_checksum, actual_checksum,
                )
                return Response(
                    {"error": "File integrity check failed."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        file_handle = backend.open(storage_name)
        response = FileResponse(
            file_handle,
            content_type=content_type,
            as_attachment=True,
            filename=download_name,
        )
        return response

    @action(detail=True, methods=["get"], url_path="versions")
    def versions(self, request, pk=None):
        """List all versions of a document."""
        doc = self.get_object()
        versions = doc.version_history.all()
        serializer = DocumentVersionSerializer(versions, many=True)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="versions/(?P<version_id>[0-9]+)/activate",
    )
    def activate_version(self, request, pk=None, version_id=None):
        """Activate a specific version of the document."""
        doc = self.get_object()
        try:
            version = doc.version_history.get(pk=version_id)
        except DocumentVersion.DoesNotExist:
            raise Http404("Version not found.")

        # Deactivate all versions, then activate the selected one
        doc.version_history.update(is_active=False)
        version.is_active = True
        version.save(update_fields=["is_active"])

        return Response(DocumentVersionSerializer(version).data)

    @action(detail=True, methods=["get"], url_path="versions/compare")
    def compare_versions(self, request, pk=None):
        """Compare two document versions and return an HTML diff.

        Query params:
          v1 -- ID of the first version
          v2 -- ID of the second version

        Returns:
          { "v1": <version_data>, "v2": <version_data>, "diff_html": "<html>" }
        """
        doc = self.get_object()

        v1_id = request.query_params.get("v1")
        v2_id = request.query_params.get("v2")

        if not v1_id or not v2_id:
            return Response(
                {"error": "Both 'v1' and 'v2' query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            version1 = doc.version_history.get(pk=v1_id)
        except DocumentVersion.DoesNotExist:
            return Response(
                {"error": f"Version {v1_id} not found for this document."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            version2 = doc.version_history.get(pk=v2_id)
        except DocumentVersion.DoesNotExist:
            return Response(
                {"error": f"Version {v2_id} not found for this document."},
                status=status.HTTP_404_NOT_FOUND,
            )

        def _get_version_content(ver):
            """Return the text content for a version (comment + file comment fallback)."""
            parts = []
            if ver.comment:
                parts.append(ver.comment)
            if ver.file and ver.file.comment:
                parts.append(ver.file.comment)
            return "\n".join(parts) if parts else ""

        content1 = _get_version_content(version1)
        content2 = _get_version_content(version2)

        # Generate side-by-side HTML diff
        html_diff = difflib.HtmlDiff(wrapcolumn=80).make_table(
            content1.splitlines(keepends=True),
            content2.splitlines(keepends=True),
            fromdesc=f"Version {version1.version_number}",
            todesc=f"Version {version2.version_number}",
            context=True,
            numlines=3,
        )

        return Response(
            {
                "v1": DocumentVersionSerializer(version1).data,
                "v2": DocumentVersionSerializer(version2).data,
                "diff_html": html_diff,
            }
        )

    @action(detail=True, methods=["post"], url_path="files", parser_classes=[MultiPartParser])
    def upload_new_version(self, request, pk=None):
        """Upload a new file to create a new version of the document."""
        doc = self.get_object()
        file = request.FILES.get("document")
        if not file:
            return Response(
                {"error": "No file provided. Use the 'document' form field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comment = request.data.get("comment", "")

        # Calculate checksum
        sha256 = hashlib.sha256()
        for chunk in file.chunks():
            sha256.update(chunk)
        file.seek(0)
        checksum = sha256.hexdigest()

        # Create DocumentFile
        doc_file = DocumentFile.objects.create(
            document=doc,
            file=file,
            filename=file.name,
            mime_type=file.content_type or "application/octet-stream",
            checksum=checksum,
            size=file.size,
            comment=comment,
            created_by=request.user,
        )

        # Determine next version number
        last_version = doc.version_history.order_by("-version_number").first()
        next_version_num = (last_version.version_number + 1) if last_version else 1

        # Deactivate old versions, create new active version
        doc.version_history.update(is_active=False)
        version = DocumentVersion.objects.create(
            document=doc,
            version_number=next_version_num,
            comment=comment,
            is_active=True,
            file=doc_file,
            created_by=request.user,
        )

        return Response(
            DocumentVersionSerializer(version).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="bulk-export", url_name="bulk-export")
    def bulk_export(self, request):
        """Stream a ZIP archive containing the original files for requested documents.

        Request body: ``{"ids": [1, 2, 3]}``

        The response is a ``StreamingHttpResponse`` with ``Content-Type: application/zip``.
        Only documents the requesting user is permitted to view are included; unknown or
        unauthorised IDs are silently skipped.
        """
        ids = request.data.get("ids")
        if not isinstance(ids, list) or not ids:
            return Response(
                {"error": "'ids' must be a non-empty list of document IDs."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Restrict to documents the user can see
        queryset = self.get_queryset().filter(pk__in=ids)

        from storage.utils import get_storage_backend
        backend = get_storage_backend()

        def zip_generator():
            """Yield ZIP file bytes incrementally.

            Because Python's zipfile writes the central directory only on close,
            we track the write position after each entry and yield only the newly
            written bytes.  The final yield (after the context manager exits) picks
            up the central directory and end-of-central-directory records.
            """
            buffer = io.BytesIO()
            pos = 0

            with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                for doc in queryset:
                    storage_name = doc.filename
                    if not storage_name:
                        continue
                    if not backend.exists(storage_name):
                        logger.warning(
                            "bulk_export: file not found in storage for document %s (%s)",
                            doc.pk, storage_name,
                        )
                        continue

                    filename_in_zip = doc.original_filename or Path(storage_name).name
                    # Prepend document ID to avoid name collisions
                    filename_in_zip = f"{doc.pk}_{filename_in_zip}"

                    file_handle = backend.open(storage_name)
                    try:
                        zf.writestr(filename_in_zip, file_handle.read())
                    finally:
                        file_handle.close()

                    # Yield bytes written since last yield (local file header + data)
                    buffer.seek(pos)
                    chunk = buffer.read()
                    if chunk:
                        yield chunk
                    pos = buffer.tell()

            # Yield the central directory + end-of-central-directory records
            buffer.seek(pos)
            tail = buffer.read()
            if tail:
                yield tail

        response = StreamingHttpResponse(zip_generator(), content_type="application/zip")
        response["Content-Disposition"] = 'attachment; filename="docvault-export.zip"'
        return response

    @action(detail=True, methods=["get"], url_path="barcode-label", url_name="barcode-label")
    def barcode_label(self, request, pk=None):
        """Return a Code128 barcode PNG for the document's Archive Serial Number (ASN).

        Returns 404 if no ASN is set on the document.
        """
        doc = self.get_object()

        if doc.archive_serial_number is None:
            raise Http404("This document has no Archive Serial Number assigned.")

        try:
            import barcode
            from barcode.writer import ImageWriter
        except ImportError:
            logger.error(
                "python-barcode is not installed. "
                "Add 'python-barcode>=0.15' to requirements/base.txt."
            )
            return Response(
                {"error": "Barcode generation library not available."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        asn_value = str(doc.archive_serial_number)
        Code128 = barcode.get_barcode_class("code128")
        buffer = io.BytesIO()
        Code128(asn_value, writer=ImageWriter()).write(buffer)
        buffer.seek(0)

        return HttpResponse(buffer.read(), content_type="image/png")


class DocumentUploadView(APIView):
    """Accept file uploads and queue async processing."""

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get("document")
        if not file:
            return Response(
                {"error": "No file provided. Use the 'document' form field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Quota enforcement
        from notifications.quotas import check_quota
        allowed, message = check_quota(request.user)
        if not allowed:
            return Response(
                {"error": message},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Save to a temp file
        temp_dir = Path(tempfile.mkdtemp(prefix="docvault_"))
        temp_path = temp_dir / file.name
        with open(temp_path, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)

        # Create a processing task
        from processing.models import ProcessingTask
        task = ProcessingTask.objects.create(
            task_name="document_consumption",
            owner=request.user,
            status_message="Queued for processing",
        )

        # Queue async processing
        from processing.tasks import consume_document
        consume_document.delay(
            source_path=str(temp_path),
            original_filename=file.name,
            task_id=str(task.task_id),
            user_id=request.user.id,
            override_title=request.data.get("title"),
            override_document_type=request.data.get("document_type"),
            override_tags=request.data.get("tags"),
        )

        return Response(
            {
                "task_id": str(task.task_id),
                "status": "queued",
            },
            status=status.HTTP_202_ACCEPTED,
        )


class DocumentTypeViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for DocumentTypes.

    Any authenticated user can view types; only admins can create/edit/delete.
    """

    queryset = DocumentType.objects.all()
    serializer_class = DocumentTypeSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

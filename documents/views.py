"""Views for the documents module."""

import difflib
import hashlib
import io
import logging
import tempfile
import uuid
import zipfile
from pathlib import Path

from django.db import transaction
from django.db.models import Prefetch
from django.http import FileResponse, Http404, HttpResponse, StreamingHttpResponse
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from security.permissions import (
    DocVaultObjectPermissions,
    IsAdminOrReadOnly,
    get_document_for_user,
    get_objects_for_user_with_ownership,
)

from .downloads import active_original, build_document_file_response, open_document_file
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
        if getattr(self, "swagger_fake_view", False):
            return Document.objects.none()
        user = self.request.user
        queryset = Document.objects.prefetch_related(Prefetch(
            "version_history", queryset=DocumentVersion.objects.filter(is_active=True).select_related("file"),
            to_attr="_active_versions",
        ))
        if user.is_superuser:
            return queryset
        return get_objects_for_user_with_ownership(
            user, "documents.view_document", queryset,
        )

    def get_serializer_class(self):
        if self.action == "list":
            return DocumentListSerializer
        return DocumentSerializer

    def perform_create(self, serializer):
        from rest_framework.exceptions import Throttled

        from notifications.quotas import QuotaExceededError, quota_guard

        try:
            with quota_guard(self.request.user):
                serializer.save(owner=self.request.user, created_by=self.request.user)
        except QuotaExceededError as exc:
            raise Throttled(detail=str(exc)) from exc

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
        doc = get_document_for_user(
            request.user,
            pk,
            action="change",
            queryset=Document.all_objects.all(),
        )
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

        if "page" in request.query_params:
            from .previews import build_pdf_page_preview

            return build_pdf_page_preview(doc, request.query_params["page"])

        artifact = active_original(doc)
        if artifact and artifact.file.name != doc.filename:
            from PIL import Image

            from .previews import build_pdf_page_preview

            if artifact.mime_type == "application/pdf":
                page = build_pdf_page_preview(doc, 1)
                image_source = io.BytesIO(page.content)
            elif artifact.mime_type.startswith("image/"):
                image_source = open_document_file(artifact)
            else:
                raise Http404("No thumbnail available for the active version.")
            with image_source, Image.open(image_source) as image:
                thumbnail = image.convert("RGB")
                thumbnail.thumbnail((400, 560))
                output = io.BytesIO()
                thumbnail.save(output, "WEBP")
            response = HttpResponse(output.getvalue(), content_type="image/webp")
            response["Cache-Control"] = "private, no-store"
            return response

        if not doc.thumbnail_path:
            raise Http404("No thumbnail available for this document.")

        from storage.utils import get_storage_backend
        backend = get_storage_backend()

        if not backend.exists(doc.thumbnail_path):
            raise Http404("Thumbnail file not found.")

        # ETag-based caching
        etag = hashlib.md5(doc.thumbnail_path.encode()).hexdigest()
        if request.META.get("HTTP_IF_NONE_MATCH") == etag:
            response = HttpResponse(status=304)
        else:
            file_handle = backend.open(doc.thumbnail_path)
            response = FileResponse(file_handle, content_type="image/webp")
        response["ETag"] = etag
        response["Cache-Control"] = "private, no-store"
        return response

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        """Download the document file (original or archive version)."""
        doc = self.get_object()
        version = request.query_params.get("version", "original")
        return build_document_file_response(doc, version)

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
    @transaction.atomic
    def activate_version(self, request, pk=None, version_id=None):
        """Activate a specific version of the document."""
        doc = self.get_object()
        doc = Document.objects.select_for_update().get(pk=doc.pk)
        self._check_legal_hold(doc)
        try:
            version = doc.version_history.get(pk=version_id)
        except DocumentVersion.DoesNotExist:
            raise Http404("Version not found.")

        # Deactivate all versions, then activate the selected one
        doc.version_history.update(is_active=False)
        version.is_active = True
        version.save(update_fields=["is_active"])
        from security.models import Signature

        Signature.objects.filter(document=doc).update(verified=False, verified_at=None)

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
            """Compare file text; use OCR content or comments when extraction is unavailable."""
            if ver.file and ver.file.file.name:
                try:
                    with open_document_file(ver.file) as stored:
                        if ver.file.mime_type.startswith("text/"):
                            return stored.read(5_000_000).decode("utf-8", errors="replace")
                        if ver.file.mime_type == "application/pdf":
                            from processing.parsers.pdf import PDFParser

                            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temporary:
                                temporary.write(stored.read())
                                temporary_path = Path(temporary.name)
                            try:
                                content = PDFParser()._extract_text(temporary_path)
                                if content:
                                    return content
                            finally:
                                temporary_path.unlink(missing_ok=True)
                    if ver.file.file.name == doc.filename and doc.content:
                        return doc.content
                except (FileNotFoundError, OSError):
                    logger.warning("Could not read file text for version %s", ver.pk)
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
    @transaction.atomic
    def upload_new_version(self, request, pk=None):
        """Upload a new file to create a new version of the document."""
        doc = self.get_object()
        doc = Document.objects.select_for_update().get(pk=doc.pk)
        self._check_legal_hold(doc)
        file = request.FILES.get("document")
        if not file:
            return Response(
                {"error": "No file provided. Use the 'document' form field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from collaboration.models import Checkout

        checkout = Checkout.objects.filter(document=doc).first()
        if checkout and not checkout.is_expired and checkout.block_new_uploads and checkout.user_id != request.user.pk:
            return Response({"error": "Document is checked out by another user."}, status=status.HTTP_409_CONFLICT)

        from rest_framework.exceptions import Throttled

        from notifications.quotas import QuotaExceededError, quota_guard

        registered_bytes = 0
        if not doc.version_history.exists() and doc.filename and not doc.files.filter(file=doc.filename).exists():
            from storage.utils import get_storage_backend

            backend = get_storage_backend()
            if backend.exists(doc.filename):
                registered_bytes = backend.size(doc.filename)

        try:
            with quota_guard(doc.owner, incoming_bytes=file.size + registered_bytes, incoming_documents=0):
                return self._create_file_version(doc, file, request)
        except QuotaExceededError as exc:
            raise Throttled(detail=str(exc)) from exc

    def _create_file_version(self, doc, file, request):
        # Preserve pre-versioning documents by recording their existing key; no file is moved.
        if not doc.version_history.exists() and doc.filename:
            from storage.utils import get_storage_backend

            backend = get_storage_backend()
            if backend.exists(doc.filename):
                original = doc.files.filter(file=doc.filename).first()
                if original is None:
                    original = DocumentFile.objects.create(
                        document=doc, file=doc.filename, filename=doc.original_filename or Path(doc.filename).name,
                        mime_type=doc.mime_type, checksum=doc.checksum, size=backend.size(doc.filename),
                        page_count=doc.page_count, created_by=doc.created_by,
                    )
                DocumentVersion.objects.create(document=doc, version_number=1, file=original, is_active=True)

        comment = request.data.get("comment", "")

        # Calculate checksum
        sha256 = hashlib.sha256()
        for chunk in file.chunks():
            sha256.update(chunk)
        file.seek(0)
        checksum = sha256.hexdigest()

        page_count = 0
        if file.content_type == "application/pdf":
            import pymupdf

            try:
                with pymupdf.open(stream=file.read(), filetype="pdf") as pdf:
                    page_count = len(pdf)
            except (RuntimeError, ValueError):
                return Response({"error": "The uploaded PDF is invalid."}, status=status.HTTP_400_BAD_REQUEST)
            finally:
                file.seek(0)
        elif (file.content_type or "").startswith("image/"):
            page_count = 1

        from storage.utils import get_storage_backend

        backend = get_storage_backend()
        storage_name = backend.save(f"versions/{doc.uuid}/{uuid.uuid4().hex}{Path(file.name).suffix}", file)

        # Legacy Django uploads remain readable through open_document_file.
        doc_file = DocumentFile.objects.create(
            document=doc,
            file=storage_name,
            filename=file.name,
            mime_type=file.content_type or "application/octet-stream",
            checksum=checksum,
            size=file.size,
            page_count=page_count,
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
        from security.models import Signature

        Signature.objects.filter(document=doc).update(verified=False, verified_at=None)

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
                    artifact = active_original(doc)
                    storage_name = artifact.file.name if artifact else doc.filename
                    if not storage_name:
                        continue
                    if not artifact and not backend.exists(storage_name):
                        logger.warning(
                            "bulk_export: file not found in storage for document %s (%s)",
                            doc.pk, storage_name,
                        )
                        continue

                    filename_in_zip = (
                        artifact.filename if artifact else doc.original_filename or Path(storage_name).name
                    )
                    # Prepend document ID to avoid name collisions
                    filename_in_zip = f"{doc.pk}_{filename_in_zip}"

                    file_handle = open_document_file(artifact) if artifact else backend.open(storage_name)
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

        from django.conf import settings

        asn_value = f"{getattr(settings, 'BARCODE_ASN_PREFIX', 'ASN')}{doc.archive_serial_number}"
        code128 = barcode.get_barcode_class("code128")
        buffer = io.BytesIO()
        code128(asn_value, writer=ImageWriter()).write(buffer)
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
        allowed, message = check_quota(request.user, incoming_bytes=file.size)
        if not allowed:
            return Response(
                {"error": message},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Save to a temp file
        temp_dir = Path(tempfile.mkdtemp(prefix="docvault_"))
        original_filename = Path(file.name).name
        temp_path = temp_dir / original_filename
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
            original_filename=original_filename,
            task_id=str(task.task_id),
            user_id=request.user.id,
            override_title=request.data.get("title"),
            override_document_type=request.data.get("document_type"),
            override_correspondent=request.data.get("correspondent"),
            override_tags=request.data.get("tags"),
            override_storage_path=request.data.get("storage_path"),
            cleanup_source_path=True,
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

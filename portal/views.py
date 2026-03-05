"""API views for the contributor portal."""

import logging
from datetime import timedelta

from django.conf import settings
from django.http import Http404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.models import Document

from .constants import (
    REQUEST_PARTIALLY_FULFILLED,
    REQUEST_PENDING,
    SUBMISSION_APPROVED,
    SUBMISSION_PENDING,
    SUBMISSION_REJECTED,
)
from .models import DocumentRequest, PortalConfig, PortalSubmission
from .serializers import (
    DocumentRequestListSerializer,
    DocumentRequestPublicSerializer,
    DocumentRequestSerializer,
    PortalConfigListSerializer,
    PortalConfigSerializer,
    PortalPublicSerializer,
    PortalSubmissionListSerializer,
    PortalSubmissionSerializer,
    PublicUploadSerializer,
    SubmissionReviewSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Admin Views (authenticated)
# ---------------------------------------------------------------------------


class PortalConfigViewSet(viewsets.ModelViewSet):
    """CRUD viewset for portal configurations."""

    permission_classes = [permissions.IsAuthenticated]
    queryset = PortalConfig.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return PortalConfigListSerializer
        return PortalConfigSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class DocumentRequestViewSet(viewsets.ModelViewSet):
    """CRUD viewset for document requests, with send/remind actions."""

    permission_classes = [permissions.IsAuthenticated]
    queryset = DocumentRequest.objects.select_related("portal").all()

    def get_serializer_class(self):
        if self.action == "list":
            return DocumentRequestListSerializer
        return DocumentRequestSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        """Send the document request email to the assignee."""
        doc_request = self.get_object()

        from .tasks import send_request_email

        send_request_email.delay(doc_request.pk)

        doc_request.sent_at = timezone.now()
        doc_request.save(update_fields=["sent_at"])

        return Response(
            {"status": "sending", "sent_at": doc_request.sent_at},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def remind(self, request, pk=None):
        """Send a deadline reminder to the assignee."""
        doc_request = self.get_object()

        from .tasks import send_deadline_reminder

        send_deadline_reminder.delay(doc_request.pk)

        doc_request.reminder_sent_at = timezone.now()
        doc_request.save(update_fields=["reminder_sent_at"])

        return Response(
            {"status": "reminder_sent", "reminder_sent_at": doc_request.reminder_sent_at},
            status=status.HTTP_200_OK,
        )


class PortalSubmissionListView(APIView):
    """GET /api/v1/portal-submissions/ — Admin review queue."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = PortalSubmission.objects.select_related(
            "portal", "request", "reviewed_by",
        )

        # Filters
        portal_id = request.query_params.get("portal")
        if portal_id:
            qs = qs.filter(portal_id=portal_id)

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        request_id = request.query_params.get("request")
        if request_id:
            qs = qs.filter(request_id=request_id)

        serializer = PortalSubmissionListSerializer(qs[:100], many=True)
        return Response(serializer.data)


class PortalSubmissionReviewView(APIView):
    """PATCH /api/v1/portal-submissions/{id}/review/ — Approve or reject."""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            submission = PortalSubmission.objects.select_related(
                "portal", "request",
            ).get(pk=pk)
        except PortalSubmission.DoesNotExist:
            raise Http404("Submission not found.")

        if submission.status != SUBMISSION_PENDING:
            return Response(
                {"error": "This submission has already been reviewed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SubmissionReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        review_notes = serializer.validated_data.get("review_notes", "")

        submission.status = new_status
        submission.review_notes = review_notes
        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()

        if new_status == SUBMISSION_APPROVED:
            # Create a Document from the submission file
            document = Document.objects.create(
                title=submission.original_filename,
                original_filename=submission.original_filename,
                document_type=submission.portal.default_document_type,
                owner=request.user,
                created_by=request.user,
            )
            # Apply default tags from the portal
            default_tags = submission.portal.default_tags.all()
            if default_tags.exists():
                document.tags.set(default_tags)

            submission.ingested_document = document
            logger.info(
                "Approved submission %s -> created document %s",
                submission.pk, document.pk,
            )

        submission.save()

        return Response(PortalSubmissionSerializer(submission).data)


# ---------------------------------------------------------------------------
# Public Views (no auth)
# ---------------------------------------------------------------------------


def _get_client_ip(request):
    """Extract client IP address from the request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _check_rate_limit(ip_address):
    """
    Check whether the IP has exceeded the upload rate limit.

    Returns True if the request should be blocked.
    """
    rate_limit = getattr(settings, "PORTAL_UPLOAD_RATE_LIMIT", 10)
    one_hour_ago = timezone.now() - timedelta(hours=1)
    recent_count = PortalSubmission.objects.filter(
        ip_address=ip_address,
        submitted_at__gte=one_hour_ago,
    ).count()
    return recent_count >= rate_limit


def _validate_upload(portal, uploaded_file):
    """
    Validate the uploaded file against the portal configuration.

    Returns an error message string if invalid, or None if valid.
    """
    # Check file size
    max_bytes = portal.max_file_size_mb * 1024 * 1024
    if uploaded_file.size > max_bytes:
        return f"File size exceeds the maximum of {portal.max_file_size_mb} MB."

    # Check MIME type
    if portal.allowed_mime_types:
        if uploaded_file.content_type not in portal.allowed_mime_types:
            return (
                f"File type '{uploaded_file.content_type}' is not allowed. "
                f"Accepted types: {', '.join(portal.allowed_mime_types)}"
            )

    return None


class PublicPortalView(APIView):
    """GET /api/v1/portal/{slug}/ — Public portal information."""

    permission_classes = []
    authentication_classes = []

    def get(self, request, slug):
        try:
            portal = PortalConfig.objects.get(slug=slug, is_active=True)
        except PortalConfig.DoesNotExist:
            raise Http404("Portal not found.")

        return Response(PortalPublicSerializer(portal).data)


class PublicPortalUploadView(APIView):
    """POST /api/v1/portal/{slug}/upload/ — Public file upload (rate limited)."""

    permission_classes = []
    authentication_classes = []

    def post(self, request, slug):
        try:
            portal = PortalConfig.objects.get(slug=slug, is_active=True)
        except PortalConfig.DoesNotExist:
            raise Http404("Portal not found.")

        # Rate limiting
        ip_address = _get_client_ip(request)
        if _check_rate_limit(ip_address):
            return Response(
                {"error": "Upload rate limit exceeded. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = PublicUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]

        # Validate against portal config
        error = _validate_upload(portal, uploaded_file)
        if error:
            return Response(
                {"error": error},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check required fields
        if portal.require_email and not serializer.validated_data.get("email"):
            return Response(
                {"error": "Email address is required for this portal."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if portal.require_name and not serializer.validated_data.get("name"):
            return Response(
                {"error": "Name is required for this portal."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        submission = PortalSubmission.objects.create(
            portal=portal,
            file=uploaded_file,
            original_filename=uploaded_file.name,
            submitter_email=serializer.validated_data.get("email", ""),
            submitter_name=serializer.validated_data.get("name", ""),
            metadata=serializer.validated_data.get("metadata", {}),
            ip_address=ip_address,
        )

        logger.info(
            "Portal upload: portal=%s, file=%s, ip=%s",
            portal.slug, uploaded_file.name, ip_address,
        )

        return Response(
            {
                "id": submission.pk,
                "original_filename": submission.original_filename,
                "submitted_at": submission.submitted_at,
            },
            status=status.HTTP_201_CREATED,
        )


class PublicRequestView(APIView):
    """GET /api/v1/request/{token}/ — Public request information."""

    permission_classes = []
    authentication_classes = []

    def get(self, request, token):
        try:
            doc_request = DocumentRequest.objects.select_related("portal").get(
                token=token,
                portal__is_active=True,
            )
        except DocumentRequest.DoesNotExist:
            raise Http404("Request not found.")

        return Response(DocumentRequestPublicSerializer(doc_request).data)


class PublicRequestUploadView(APIView):
    """POST /api/v1/request/{token}/upload/ — Upload against a document request."""

    permission_classes = []
    authentication_classes = []

    def post(self, request, token):
        try:
            doc_request = DocumentRequest.objects.select_related("portal").get(
                token=token,
                portal__is_active=True,
            )
        except DocumentRequest.DoesNotExist:
            raise Http404("Request not found.")

        if doc_request.status not in (REQUEST_PENDING, REQUEST_PARTIALLY_FULFILLED):
            return Response(
                {"error": "This request is no longer accepting submissions."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        portal = doc_request.portal

        # Rate limiting
        ip_address = _get_client_ip(request)
        if _check_rate_limit(ip_address):
            return Response(
                {"error": "Upload rate limit exceeded. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = PublicUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]

        # Validate against portal config
        error = _validate_upload(portal, uploaded_file)
        if error:
            return Response(
                {"error": error},
                status=status.HTTP_400_BAD_REQUEST,
            )

        submission = PortalSubmission.objects.create(
            portal=portal,
            request=doc_request,
            file=uploaded_file,
            original_filename=uploaded_file.name,
            submitter_email=serializer.validated_data.get("email", "") or doc_request.assignee_email,
            submitter_name=serializer.validated_data.get("name", "") or doc_request.assignee_name,
            metadata=serializer.validated_data.get("metadata", {}),
            ip_address=ip_address,
        )

        # Update request status to partially fulfilled
        if doc_request.status == REQUEST_PENDING:
            doc_request.status = REQUEST_PARTIALLY_FULFILLED
            doc_request.save(update_fields=["status"])

        logger.info(
            "Request upload: request=%s, file=%s, ip=%s",
            doc_request.pk, uploaded_file.name, ip_address,
        )

        return Response(
            {
                "id": submission.pk,
                "original_filename": submission.original_filename,
                "submitted_at": submission.submitted_at,
            },
            status=status.HTTP_201_CREATED,
        )

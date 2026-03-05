"""API views for the e-signatures app."""

import logging

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .constants import REQUEST_CANCELLED, REQUEST_COMPLETED, REQUEST_EXPIRED
from .engine import (
    InvalidStateError,
    ValidationError as EngineValidationError,
    cancel_request,
    complete_signing,
    decline_signing,
    record_page_view,
    record_view,
    send_request,
)
from .models import SignatureAuditEvent, SignatureRequest, Signer
from .serializers import (
    DeclineSerializer,
    PublicSigningSerializer,
    SignatureAuditEventSerializer,
    SignatureRequestCreateSerializer,
    SignatureRequestListSerializer,
    SignatureRequestSerializer,
    SigningCompleteSerializer,
    ViewPageSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_client_ip(request):
    """Extract client IP address from the request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class SigningRateThrottle(AnonRateThrottle):
    """Rate throttle for public signing endpoints."""

    rate = "30/minute"


# ---------------------------------------------------------------------------
# Authenticated Views
# ---------------------------------------------------------------------------


class SignatureRequestViewSet(viewsets.ModelViewSet):
    """
    CRUD viewset for signature requests.

    Filters to requests created by the authenticated user.
    Provides send, cancel, remind, and certificate actions.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            SignatureRequest.objects
            .filter(created_by=self.request.user)
            .select_related("document")
            .prefetch_related("signers", "fields")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return SignatureRequestListSerializer
        return SignatureRequestSerializer

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        """Send the signature request to signers."""
        sig_request = self.get_object()

        try:
            send_request(sig_request)
        except (InvalidStateError, EngineValidationError) as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"status": "sent", "sent_at": timezone.now().isoformat()},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel the signature request."""
        sig_request = self.get_object()

        try:
            cancel_request(sig_request, user=request.user)
        except InvalidStateError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"status": "cancelled"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def remind(self, request, pk=None):
        """Send a reminder to pending signers."""
        sig_request = self.get_object()

        from .tasks import send_signature_reminder

        send_signature_reminder.delay(sig_request.pk)

        return Response(
            {"status": "reminder_queued"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def certificate(self, request, pk=None):
        """Download the completion certificate PDF."""
        sig_request = self.get_object()

        if not sig_request.certificate_pdf:
            return Response(
                {"error": "Certificate not yet generated."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return FileResponse(
            sig_request.certificate_pdf.open("rb"),
            content_type="application/pdf",
            as_attachment=True,
            filename=f"certificate_{sig_request.pk}.pdf",
        )


class DocumentSignatureRequestView(APIView):
    """POST /api/v1/documents/{document_id}/signature-request/

    Create a new signature request for a specific document with nested
    signers and fields in a single call.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, document_id):
        data = request.data.copy()
        data["document"] = document_id

        serializer = SignatureRequestCreateSerializer(
            data=data,
            context={"user": request.user},
        )
        serializer.is_valid(raise_exception=True)
        sig_request = serializer.save()

        return Response(
            SignatureRequestSerializer(sig_request).data,
            status=status.HTTP_201_CREATED,
        )


class SignatureRequestAuditView(APIView):
    """GET /api/v1/signature-requests/{pk}/audit/

    Retrieve the full audit trail for a signature request.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        sig_request = get_object_or_404(
            SignatureRequest,
            pk=pk,
            created_by=request.user,
        )
        events = (
            sig_request.audit_events
            .select_related("signer")
            .all()
        )
        serializer = SignatureAuditEventSerializer(events, many=True)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Public Views (no auth)
# ---------------------------------------------------------------------------

_TERMINAL_STATUSES = (REQUEST_COMPLETED, REQUEST_CANCELLED, REQUEST_EXPIRED)


def _get_signer_or_404(token):
    """Look up a Signer by token, raising 404 if not found."""
    try:
        return Signer.objects.select_related(
            "request", "request__document",
        ).get(token=token)
    except Signer.DoesNotExist:
        raise Http404("Signer not found.")


def _check_request_active(signer):
    """
    Check that the signer's request is still active.

    Returns an error Response if the request is in a terminal state
    or has expired, otherwise returns None.
    """
    sig_request = signer.request

    # Check expiration
    if sig_request.expiration and sig_request.expiration < timezone.now():
        return Response(
            {"error": "This signature request has expired."},
            status=status.HTTP_410_GONE,
        )

    if sig_request.status in _TERMINAL_STATUSES:
        return Response(
            {"error": f"This signature request is {sig_request.status}."},
            status=status.HTTP_410_GONE,
        )

    return None


class PublicSigningView(APIView):
    """GET /api/v1/sign/{token}/

    Public endpoint returning signer info, document details, and fields.
    Also records that the signer has viewed the request.
    """

    permission_classes = []
    authentication_classes = []
    throttle_classes = [SigningRateThrottle]

    def get(self, request, token):
        signer = _get_signer_or_404(token)
        error_response = _check_request_active(signer)
        if error_response:
            return error_response

        ip_address = _get_client_ip(request)
        record_view(signer, ip_address=ip_address)

        # Refresh signer after state change
        signer.refresh_from_db()
        serializer = PublicSigningSerializer(signer)
        return Response(serializer.data)


class PublicViewPageView(APIView):
    """POST /api/v1/sign/{token}/view_page/

    Record that the signer has viewed a specific page.
    """

    permission_classes = []
    authentication_classes = []
    throttle_classes = [SigningRateThrottle]

    def post(self, request, token):
        signer = _get_signer_or_404(token)
        error_response = _check_request_active(signer)
        if error_response:
            return error_response

        serializer = ViewPageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = _get_client_ip(request)
        page = serializer.validated_data["page"]

        record_page_view(signer, page, ip_address=ip_address)

        return Response(
            {"status": "recorded", "page": page},
            status=status.HTTP_200_OK,
        )


class PublicSigningCompleteView(APIView):
    """POST /api/v1/sign/{token}/complete/

    Submit field values and complete the signing process.
    """

    permission_classes = []
    authentication_classes = []
    throttle_classes = [SigningRateThrottle]

    def post(self, request, token):
        signer = _get_signer_or_404(token)
        error_response = _check_request_active(signer)
        if error_response:
            return error_response

        serializer = SigningCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = _get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        try:
            complete_signing(
                signer,
                field_values=serializer.validated_data["fields"],
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except (InvalidStateError, EngineValidationError) as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"status": "signed", "signed_at": signer.signed_at.isoformat()},
            status=status.HTTP_200_OK,
        )


class PublicSigningDeclineView(APIView):
    """POST /api/v1/sign/{token}/decline/

    Decline to sign the document.
    """

    permission_classes = []
    authentication_classes = []
    throttle_classes = [SigningRateThrottle]

    def post(self, request, token):
        signer = _get_signer_or_404(token)
        error_response = _check_request_active(signer)
        if error_response:
            return error_response

        serializer = DeclineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = _get_client_ip(request)
        reason = serializer.validated_data.get("reason", "")

        try:
            decline_signing(signer, reason=reason, ip_address=ip_address)
        except InvalidStateError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"status": "declined"},
            status=status.HTTP_200_OK,
        )

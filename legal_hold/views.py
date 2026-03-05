"""Views for the legal_hold module."""

import logging

from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .constants import ACTIVE, DRAFT
from .engine import activate_hold, release_hold
from .models import (
    LegalHold,
    LegalHoldCustodian,
)
from .serializers import (
    CustodianAcknowledgeSerializer,
    LegalHoldCreateSerializer,
    LegalHoldCustodianSerializer,
    LegalHoldDocumentSerializer,
    LegalHoldListSerializer,
    LegalHoldReleaseSerializer,
    LegalHoldSerializer,
)

logger = logging.getLogger(__name__)


class IsAdminOrStaff(permissions.BasePermission):
    """Allow access only to admin or staff users."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )


class LegalHoldViewSet(viewsets.ModelViewSet):
    """
    CRUD and lifecycle operations for Legal Holds.

    Permissions: admin/staff only for all operations.
    """

    queryset = LegalHold.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsAdminOrStaff]
    search_fields = ["name", "matter_number", "description"]
    ordering_fields = ["name", "status", "created_at", "activated_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return LegalHoldListSerializer
        if self.action == "create":
            return LegalHoldCreateSerializer
        if self.action == "release":
            return LegalHoldReleaseSerializer
        return LegalHoldSerializer

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """Activate a draft hold: evaluate criteria and capture documents."""
        hold = self.get_object()
        if hold.status != DRAFT:
            return Response(
                {"error": f"Cannot activate hold in '{hold.status}' status. Must be '{DRAFT}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        count = activate_hold(hold)
        hold.refresh_from_db()
        return Response(
            {
                "status": "activated",
                "documents_captured": count,
                "hold": LegalHoldSerializer(hold).data,
            }
        )

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        """Release an active hold."""
        hold = self.get_object()
        if hold.status != ACTIVE:
            return Response(
                {"error": f"Cannot release hold in '{hold.status}' status. Must be '{ACTIVE}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = LegalHoldReleaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "")
        release_hold(hold, request.user, reason)
        hold.refresh_from_db()
        return Response(
            {
                "status": "released",
                "hold": LegalHoldSerializer(hold).data,
            }
        )

    @action(detail=True, methods=["get"])
    def documents(self, request, pk=None):
        """List all documents held by this legal hold."""
        hold = self.get_object()
        held_docs = hold.held_documents.select_related("document").all()
        serializer = LegalHoldDocumentSerializer(held_docs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def custodians(self, request, pk=None):
        """List all custodians for this legal hold."""
        hold = self.get_object()
        custodians = hold.custodians.select_related("user").all()
        serializer = LegalHoldCustodianSerializer(custodians, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def notify(self, request, pk=None):
        """Re-send custodian notification emails."""
        hold = self.get_object()
        if hold.status != ACTIVE:
            return Response(
                {"error": "Can only notify custodians for active holds."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .tasks import notify_custodians

        notify_custodians.delay(hold.pk)
        return Response({"status": "notifications_queued"})

    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        """Export a JSON snapshot of hold details."""
        hold = self.get_object()
        from .serializers import LegalHoldCriteriaSerializer

        data = LegalHoldSerializer(hold).data
        data["criteria"] = LegalHoldCriteriaSerializer(
            hold.criteria.all(), many=True
        ).data
        data["custodians"] = LegalHoldCustodianSerializer(
            hold.custodians.select_related("user").all(), many=True
        ).data
        data["documents"] = LegalHoldDocumentSerializer(
            hold.held_documents.select_related("document").all(), many=True
        ).data
        return Response(data)


class CustodianAcknowledgeView(APIView):
    """
    POST endpoint for custodians to acknowledge a legal hold.

    Any authenticated user who is a custodian on the specified hold
    can acknowledge it.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, hold_id):
        serializer = CustodianAcknowledgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            custodian = LegalHoldCustodian.objects.get(
                hold_id=hold_id, user=request.user
            )
        except LegalHoldCustodian.DoesNotExist:
            return Response(
                {"error": "You are not a custodian for this hold."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if custodian.acknowledged:
            return Response(
                {"status": "already_acknowledged", "acknowledged_at": custodian.acknowledged_at}
            )

        custodian.acknowledged = True
        custodian.acknowledged_at = timezone.now()
        custodian.save(update_fields=["acknowledged", "acknowledged_at"])

        return Response(
            {
                "status": "acknowledged",
                "acknowledged_at": custodian.acknowledged_at,
            }
        )

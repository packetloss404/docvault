"""Views for the physical_records module."""

import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.models import Document

from .constants import CHECKED_OUT, RETURNED
from .models import ChargeOut, DestructionCertificate, PhysicalLocation, PhysicalRecord
from .serializers import (
    BarcodeCheckoutSerializer,
    ChargeInSerializer,
    ChargeOutCreateSerializer,
    ChargeOutSerializer,
    DestructionCertificateCreateSerializer,
    DestructionCertificateSerializer,
    PhysicalLocationSerializer,
    PhysicalLocationTreeSerializer,
    PhysicalRecordCreateSerializer,
    PhysicalRecordSerializer,
)

logger = logging.getLogger(__name__)


class PhysicalLocationViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for PhysicalLocation.

    Includes a `tree` action to return the hierarchical location tree.
    """

    queryset = PhysicalLocation.objects.all()
    serializer_class = PhysicalLocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name", "barcode"]
    ordering_fields = ["name", "location_type"]
    ordering = ["tree_id", "lft"]

    @action(detail=False, methods=["get"])
    def tree(self, request):
        """Return the full location hierarchy as a nested tree."""
        root_nodes = PhysicalLocation.objects.root_nodes()
        serializer = PhysicalLocationTreeSerializer(root_nodes, many=True)
        return Response(serializer.data)


class PhysicalRecordViewSet(viewsets.ModelViewSet):
    """CRUD operations for PhysicalRecord."""

    queryset = PhysicalRecord.objects.select_related("document", "location").all()
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["barcode", "document__title", "notes"]
    ordering_fields = ["created_at", "condition"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return PhysicalRecordCreateSerializer
        return PhysicalRecordSerializer

    def perform_create(self, serializer):
        instance = serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        # Update location count
        if instance.location:
            instance.location.current_count = instance.location.records.count()
            instance.location.save(update_fields=["current_count"])

    def perform_update(self, serializer):
        old_location = self.get_object().location
        instance = serializer.save(updated_by=self.request.user)
        # Update old location count
        if old_location and old_location != instance.location:
            old_location.current_count = old_location.records.count()
            old_location.save(update_fields=["current_count"])
        # Update new location count
        if instance.location:
            instance.location.current_count = instance.location.records.count()
            instance.location.save(update_fields=["current_count"])


class ChargeOutView(APIView):
    """POST to check out a physical record for a document."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, document_id):
        document = get_object_or_404(Document, pk=document_id)
        physical_record = get_object_or_404(PhysicalRecord, document=document)

        # Check if already checked out
        active_checkout = physical_record.charge_outs.filter(
            status=CHECKED_OUT
        ).first()
        if active_checkout:
            return Response(
                {"error": "This record is already checked out."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ChargeOutCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        charge_out = ChargeOut.objects.create(
            physical_record=physical_record,
            user=request.user,
            expected_return=serializer.validated_data["expected_return"],
            notes=serializer.validated_data.get("notes", ""),
            status=CHECKED_OUT,
        )

        # Update location count (record is leaving)
        if physical_record.location:
            location = physical_record.location
            location.current_count = max(0, location.current_count - 1)
            location.save(update_fields=["current_count"])

        return Response(
            ChargeOutSerializer(charge_out).data,
            status=status.HTTP_201_CREATED,
        )


class ChargeInView(APIView):
    """POST to return (charge in) a physical record for a document."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, document_id):
        document = get_object_or_404(Document, pk=document_id)
        physical_record = get_object_or_404(PhysicalRecord, document=document)

        active_checkout = physical_record.charge_outs.filter(
            status=CHECKED_OUT
        ).first()
        if not active_checkout:
            return Response(
                {"error": "This record is not currently checked out."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ChargeInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        active_checkout.returned_at = timezone.now()
        active_checkout.status = RETURNED
        if serializer.validated_data.get("notes"):
            active_checkout.notes = (
                active_checkout.notes + "\n" + serializer.validated_data["notes"]
            ).strip()
        active_checkout.save(update_fields=["returned_at", "status", "notes"])

        # Update location count (record is returning)
        if physical_record.location:
            location = physical_record.location
            location.current_count = location.current_count + 1
            location.save(update_fields=["current_count"])

        return Response(ChargeOutSerializer(active_checkout).data)


class BarcodeCheckoutView(APIView):
    """POST with barcode to find a record and check it out."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        physical_record = get_object_or_404(PhysicalRecord, pk=pk)

        serializer = BarcodeCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        barcode = serializer.validated_data["barcode"]

        # Verify barcode matches
        if physical_record.barcode != barcode:
            return Response(
                {"error": "Barcode does not match the physical record."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if already checked out
        active_checkout = physical_record.charge_outs.filter(
            status=CHECKED_OUT
        ).first()
        if active_checkout:
            return Response(
                {"error": "This record is already checked out."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        charge_out = ChargeOut.objects.create(
            physical_record=physical_record,
            user=request.user,
            expected_return=serializer.validated_data["expected_return"],
            notes=serializer.validated_data.get("notes", ""),
            status=CHECKED_OUT,
        )

        # Update location count
        if physical_record.location:
            location = physical_record.location
            location.current_count = max(0, location.current_count - 1)
            location.save(update_fields=["current_count"])

        return Response(
            ChargeOutSerializer(charge_out).data,
            status=status.HTTP_201_CREATED,
        )


class ChargeOutListView(APIView):
    """GET list of all charge-outs with optional filter by status and user."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = ChargeOut.objects.select_related(
            "physical_record", "user"
        ).all()

        # Filter by status
        charge_status = request.query_params.get("status")
        if charge_status:
            queryset = queryset.filter(status=charge_status)

        # Filter by user
        user_id = request.query_params.get("user")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        serializer = ChargeOutSerializer(queryset, many=True)
        return Response(serializer.data)


class OverdueChargeOutView(APIView):
    """GET list of overdue charge-outs."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        queryset = ChargeOut.objects.select_related(
            "physical_record", "user"
        ).filter(
            status=CHECKED_OUT,
            expected_return__lt=now,
        )

        serializer = ChargeOutSerializer(queryset, many=True)
        return Response(serializer.data)


class DestructionCertificateView(APIView):
    """POST to generate a destruction certificate for a physical record."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        physical_record = get_object_or_404(PhysicalRecord, pk=pk)

        serializer = DestructionCertificateCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        certificate = DestructionCertificate.objects.create(
            physical_record=physical_record,
            destroyed_at=timezone.now(),
            destroyed_by=request.user,
            method=serializer.validated_data["method"],
            witness=serializer.validated_data.get("witness", ""),
            notes=serializer.validated_data.get("notes", ""),
        )

        return Response(
            DestructionCertificateSerializer(certificate).data,
            status=status.HTTP_201_CREATED,
        )

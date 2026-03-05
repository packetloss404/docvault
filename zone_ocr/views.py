"""API views for the Zone OCR module."""

import logging

from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.models import Document

from .extraction import (
    apply_preprocessing,
    extract_field_from_content,
    match_template,
    populate_custom_field,
    validate_value,
)
from .models import ZoneOCRField, ZoneOCRResult, ZoneOCRTemplate
from .serializers import (
    TestTemplateSerializer,
    ZoneOCRFieldSerializer,
    ZoneOCRResultCorrectionSerializer,
    ZoneOCRResultSerializer,
    ZoneOCRTemplateListSerializer,
    ZoneOCRTemplateSerializer,
)

logger = logging.getLogger(__name__)


class ZoneOCRTemplateViewSet(viewsets.ModelViewSet):
    """CRUD operations for Zone OCR Templates.

    list:   GET    /api/v1/zone-ocr-templates/
    create: POST   /api/v1/zone-ocr-templates/
    read:   GET    /api/v1/zone-ocr-templates/{id}/
    update: PUT    /api/v1/zone-ocr-templates/{id}/
    patch:  PATCH  /api/v1/zone-ocr-templates/{id}/
    delete: DELETE /api/v1/zone-ocr-templates/{id}/
    """

    queryset = ZoneOCRTemplate.objects.prefetch_related("fields").all()
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at", "updated_at"]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action == "list":
            return ZoneOCRTemplateListSerializer
        return ZoneOCRTemplateSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class ZoneOCRFieldListCreateView(generics.ListCreateAPIView):
    """List and create fields for a specific template.

    GET  /api/v1/zone-ocr-templates/{template_id}/fields/
    POST /api/v1/zone-ocr-templates/{template_id}/fields/
    """

    serializer_class = ZoneOCRFieldSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ZoneOCRField.objects.filter(
            template_id=self.kwargs["template_id"],
        ).select_related("template", "custom_field")

    def perform_create(self, serializer):
        template = ZoneOCRTemplate.objects.get(pk=self.kwargs["template_id"])
        serializer.save(template=template)


class ZoneOCRFieldDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific field.

    GET    /api/v1/zone-ocr-templates/{template_id}/fields/{id}/
    PUT    /api/v1/zone-ocr-templates/{template_id}/fields/{id}/
    PATCH  /api/v1/zone-ocr-templates/{template_id}/fields/{id}/
    DELETE /api/v1/zone-ocr-templates/{template_id}/fields/{id}/
    """

    serializer_class = ZoneOCRFieldSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ZoneOCRField.objects.filter(
            template_id=self.kwargs["template_id"],
        ).select_related("template", "custom_field")


class ZoneOCRResultListView(generics.ListAPIView):
    """List zone OCR results with filtering support.

    GET /api/v1/zone-ocr-results/?document_id=&template_id=&confidence__lt=&reviewed=

    Supports a review queue workflow by filtering on confidence
    and reviewed status.
    """

    serializer_class = ZoneOCRResultSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ZoneOCRResult.objects.select_related(
            "template", "field", "document", "reviewed_by",
        ).all()

        # Filter by document
        document_id = self.request.query_params.get("document_id")
        if document_id:
            qs = qs.filter(document_id=document_id)

        # Filter by template
        template_id = self.request.query_params.get("template_id")
        if template_id:
            qs = qs.filter(template_id=template_id)

        # Filter by confidence threshold (for review queue)
        confidence_lt = self.request.query_params.get("confidence__lt")
        if confidence_lt:
            try:
                qs = qs.filter(confidence__lt=float(confidence_lt))
            except (ValueError, TypeError):
                pass

        # Filter by reviewed status
        reviewed = self.request.query_params.get("reviewed")
        if reviewed is not None:
            if reviewed.lower() in ("true", "1", "yes"):
                qs = qs.filter(reviewed=True)
            elif reviewed.lower() in ("false", "0", "no"):
                qs = qs.filter(reviewed=False)

        return qs


class ZoneOCRResultCorrectionView(generics.RetrieveUpdateAPIView):
    """Retrieve or correct a zone OCR result.

    GET   /api/v1/zone-ocr-results/{id}/
    PATCH /api/v1/zone-ocr-results/{id}/

    When a correction is submitted, the result is automatically
    marked as reviewed and the reviewing user is recorded.
    """

    queryset = ZoneOCRResult.objects.select_related(
        "template", "field", "document", "reviewed_by",
    ).all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return ZoneOCRResultCorrectionSerializer
        return ZoneOCRResultSerializer

    def perform_update(self, serializer):
        serializer.save(
            reviewed=True,
            reviewed_by=self.request.user,
        )


class TestTemplateView(APIView):
    """Test a zone OCR template against a specific document.

    POST /api/v1/zone-ocr-templates/{template_id}/test/

    Runs zone OCR extraction for the specified template on the given
    document and returns the results without persisting them.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, template_id):
        serializer = TestTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Load the template
        try:
            template = ZoneOCRTemplate.objects.prefetch_related(
                "fields",
            ).get(pk=template_id)
        except ZoneOCRTemplate.DoesNotExist:
            return Response(
                {"error": "Template not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Load the document
        document_id = serializer.validated_data["document_id"]
        try:
            document = Document.objects.get(pk=document_id)
        except Document.DoesNotExist:
            return Response(
                {"error": "Document not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Run extraction on each field
        results = []
        for zone_field in template.fields.all():
            extracted_value, confidence = extract_field_from_content(
                content=document.content,
                field_name=zone_field.name,
                field_type=zone_field.field_type,
                preprocessing=zone_field.preprocessing,
            )

            is_valid = validate_value(
                extracted_value,
                zone_field.field_type,
                zone_field.validation_regex,
            )

            results.append({
                "field_id": zone_field.id,
                "field_name": zone_field.name,
                "field_type": zone_field.field_type,
                "extracted_value": extracted_value,
                "confidence": confidence,
                "is_valid": is_valid,
                "custom_field_id": (
                    zone_field.custom_field_id if zone_field.custom_field else None
                ),
            })

        return Response({
            "template_id": template.id,
            "template_name": template.name,
            "document_id": document.id,
            "document_title": document.title,
            "results": results,
        })

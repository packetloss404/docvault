"""Serializers for the e-signatures app."""

from django.db import transaction
from rest_framework import serializers

from .constants import (
    FIELD_TYPE_CHOICES,
    SIGNER_STATUS_CHOICES,
    VERIFICATION_METHOD_CHOICES,
)
from .models import (
    SignatureAuditEvent,
    SignatureField,
    SignatureRequest,
    Signer,
)


# ---------------------------------------------------------------------------
# Core model serializers
# ---------------------------------------------------------------------------


class SignerSerializer(serializers.ModelSerializer):
    """Full serializer for Signer instances."""

    class Meta:
        model = Signer
        fields = [
            "id",
            "request",
            "name",
            "email",
            "role",
            "order",
            "token",
            "status",
            "signed_at",
            "ip_address",
            "user_agent",
            "verification_method",
            "viewed_pages",
        ]
        read_only_fields = [
            "id",
            "token",
            "status",
            "signed_at",
            "ip_address",
            "user_agent",
            "viewed_pages",
        ]


class SignatureFieldSerializer(serializers.ModelSerializer):
    """Full serializer for SignatureField instances with coordinate validation."""

    class Meta:
        model = SignatureField
        fields = [
            "id",
            "request",
            "signer",
            "page",
            "x",
            "y",
            "width",
            "height",
            "field_type",
            "required",
            "order",
            "value",
            "signed_at",
        ]
        read_only_fields = ["id", "value", "signed_at"]

    def validate_x(self, value):
        if not 0.0 <= value <= 1.0:
            raise serializers.ValidationError(
                "X coordinate must be between 0.0 and 1.0."
            )
        return value

    def validate_y(self, value):
        if not 0.0 <= value <= 1.0:
            raise serializers.ValidationError(
                "Y coordinate must be between 0.0 and 1.0."
            )
        return value

    def validate_width(self, value):
        if not 0.0 <= value <= 1.0:
            raise serializers.ValidationError(
                "Width must be between 0.0 and 1.0."
            )
        return value

    def validate_height(self, value):
        if not 0.0 <= value <= 1.0:
            raise serializers.ValidationError(
                "Height must be between 0.0 and 1.0."
            )
        return value


# ---------------------------------------------------------------------------
# Signature request serializers
# ---------------------------------------------------------------------------


class SignatureRequestSerializer(serializers.ModelSerializer):
    """
    Full serializer for SignatureRequest with nested signers and fields (read).
    """

    signers = SignerSerializer(many=True, read_only=True)
    fields_data = SignatureFieldSerializer(
        source="fields", many=True, read_only=True,
    )
    signer_count = serializers.SerializerMethodField()
    field_count = serializers.SerializerMethodField()

    class Meta:
        model = SignatureRequest
        fields = [
            "id",
            "document",
            "title",
            "message",
            "status",
            "signing_order",
            "expiration",
            "completed_at",
            "certificate_pdf",
            "signers",
            "fields_data",
            "signer_count",
            "field_count",
            "created_at",
            "updated_at",
            "created_by",
        ]
        read_only_fields = [
            "id",
            "status",
            "completed_at",
            "certificate_pdf",
            "signer_count",
            "field_count",
            "created_at",
            "updated_at",
            "created_by",
        ]

    def get_signer_count(self, obj):
        return obj.signers.count()

    def get_field_count(self, obj):
        return obj.fields.count()


class SignatureRequestListSerializer(serializers.ModelSerializer):
    """Lightweight list serializer for signature requests."""

    signer_count = serializers.SerializerMethodField()
    document_title = serializers.CharField(
        source="document.title", read_only=True,
    )

    class Meta:
        model = SignatureRequest
        fields = [
            "id",
            "document",
            "document_title",
            "title",
            "status",
            "signing_order",
            "expiration",
            "completed_at",
            "signer_count",
            "created_at",
        ]
        read_only_fields = fields

    def get_signer_count(self, obj):
        return obj.signers.count()


# ---------------------------------------------------------------------------
# Create serializer with nested writes
# ---------------------------------------------------------------------------


class SignerCreateSerializer(serializers.Serializer):
    """Inline signer data for request creation."""

    name = serializers.CharField(max_length=256)
    email = serializers.EmailField()
    role = serializers.CharField(max_length=128, required=False, default="")
    order = serializers.IntegerField(min_value=0, default=0)
    verification_method = serializers.ChoiceField(
        choices=VERIFICATION_METHOD_CHOICES,
        default="email",
    )


class FieldCreateSerializer(serializers.Serializer):
    """Inline field data for request creation."""

    signer_index = serializers.IntegerField(
        min_value=0,
        help_text="Index into the signers list (0-based).",
    )
    page = serializers.IntegerField(min_value=0)
    x = serializers.FloatField(min_value=0.0, max_value=1.0)
    y = serializers.FloatField(min_value=0.0, max_value=1.0)
    width = serializers.FloatField(min_value=0.0, max_value=1.0)
    height = serializers.FloatField(min_value=0.0, max_value=1.0)
    field_type = serializers.ChoiceField(choices=FIELD_TYPE_CHOICES)
    required = serializers.BooleanField(default=True)
    order = serializers.IntegerField(min_value=0, default=0)


class SignatureRequestCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a signature request with nested signers and fields.

    Expects:
    {
        "document": <id>,
        "title": "...",
        "message": "...",
        "signing_order": "sequential",
        "expiration": "2026-04-01T00:00:00Z",
        "signers": [
            {"name": "...", "email": "...", "order": 0},
        ],
        "fields": [
            {"signer_index": 0, "page": 1, "x": 0.1, "y": 0.5, ...},
        ]
    }
    """

    document = serializers.IntegerField()
    title = serializers.CharField(max_length=256)
    message = serializers.CharField(required=False, default="", allow_blank=True)
    signing_order = serializers.ChoiceField(
        choices=[("sequential", "Sequential"), ("parallel", "Parallel")],
        default="sequential",
    )
    expiration = serializers.DateTimeField(required=False, allow_null=True, default=None)
    signers = SignerCreateSerializer(many=True)
    fields = FieldCreateSerializer(many=True)

    def validate_document(self, value):
        from documents.models import Document

        try:
            return Document.objects.get(pk=value)
        except Document.DoesNotExist:
            raise serializers.ValidationError(
                f"Document with id {value} does not exist."
            )

    def validate_signers(self, value):
        if not value:
            raise serializers.ValidationError("At least one signer is required.")
        return value

    def validate_fields(self, value):
        if not value:
            raise serializers.ValidationError("At least one field is required.")
        return value

    def validate(self, attrs):
        signers = attrs.get("signers", [])
        fields = attrs.get("fields", [])

        # Validate signer_index references
        signer_count = len(signers)
        for field_data in fields:
            idx = field_data["signer_index"]
            if idx >= signer_count:
                raise serializers.ValidationError(
                    f"Field references signer_index {idx}, but only "
                    f"{signer_count} signers were provided."
                )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = self.context.get("user")
        signers_data = validated_data.pop("signers")
        fields_data = validated_data.pop("fields")

        sig_request = SignatureRequest.objects.create(
            created_by=user,
            updated_by=user,
            **validated_data,
        )

        # Create signers and keep ordered references
        signer_instances = []
        for signer_data in signers_data:
            signer = Signer.objects.create(
                request=sig_request,
                **signer_data,
            )
            signer_instances.append(signer)

        # Create fields, linking to signer by index
        for field_data in fields_data:
            signer_index = field_data.pop("signer_index")
            SignatureField.objects.create(
                request=sig_request,
                signer=signer_instances[signer_index],
                **field_data,
            )

        # Create CREATED audit event
        from .constants import EVENT_CREATED

        SignatureAuditEvent.objects.create(
            request=sig_request,
            event_type=EVENT_CREATED,
            detail={
                "created_by": user.username if user else "unknown",
                "signer_count": len(signer_instances),
                "field_count": len(fields_data),
            },
        )

        return sig_request


# ---------------------------------------------------------------------------
# Audit event serializer
# ---------------------------------------------------------------------------


class SignatureAuditEventSerializer(serializers.ModelSerializer):
    """Read-only serializer for audit trail events."""

    signer_name = serializers.CharField(
        source="signer.name", read_only=True, default=None,
    )
    signer_email = serializers.CharField(
        source="signer.email", read_only=True, default=None,
    )

    class Meta:
        model = SignatureAuditEvent
        fields = [
            "id",
            "request",
            "signer",
            "signer_name",
            "signer_email",
            "event_type",
            "detail",
            "ip_address",
            "timestamp",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Public signing serializers
# ---------------------------------------------------------------------------


class PublicSignatureFieldSerializer(serializers.ModelSerializer):
    """Field data exposed to the public signing page."""

    class Meta:
        model = SignatureField
        fields = [
            "id",
            "page",
            "x",
            "y",
            "width",
            "height",
            "field_type",
            "required",
            "order",
            "value",
            "signed_at",
        ]
        read_only_fields = fields


class PublicSigningSerializer(serializers.Serializer):
    """
    Serializer for the public signing page.

    Returns document info, signer info, request info, and assigned fields.
    """

    # Request info
    request_id = serializers.IntegerField(source="request.pk")
    request_title = serializers.CharField(source="request.title")
    request_message = serializers.CharField(source="request.message")
    request_status = serializers.CharField(source="request.status")
    signing_order = serializers.CharField(source="request.signing_order")
    expiration = serializers.DateTimeField(source="request.expiration")

    # Document info
    document_id = serializers.IntegerField(source="request.document.pk")
    document_title = serializers.CharField(source="request.document.title")
    document_page_count = serializers.IntegerField(
        source="request.document.page_count",
    )

    # Signer info
    signer_id = serializers.IntegerField(source="pk")
    signer_name = serializers.CharField(source="name")
    signer_email = serializers.EmailField(source="email")
    signer_role = serializers.CharField(source="role")
    signer_status = serializers.CharField(source="status")
    viewed_pages = serializers.ListField(child=serializers.IntegerField())

    # Fields for this signer
    fields = PublicSignatureFieldSerializer(many=True)


class SigningCompleteSerializer(serializers.Serializer):
    """
    Serializer for the POST /sign/{token}/complete/ endpoint.

    Expects a list of field completions.
    """

    class FieldValueSerializer(serializers.Serializer):
        field_id = serializers.IntegerField()
        value = serializers.CharField(allow_blank=True)

    fields = FieldValueSerializer(many=True)

    def validate_fields(self, value):
        if not value:
            raise serializers.ValidationError(
                "At least one field value must be provided."
            )
        return value


class ViewPageSerializer(serializers.Serializer):
    """Serializer for page view tracking."""

    page = serializers.IntegerField(min_value=0)


class DeclineSerializer(serializers.Serializer):
    """Serializer for declining to sign."""

    reason = serializers.CharField(
        required=False, default="", allow_blank=True, max_length=1024,
    )

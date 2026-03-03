"""Serializers for the physical_records module."""

from rest_framework import serializers

from .models import ChargeOut, DestructionCertificate, PhysicalLocation, PhysicalRecord


class PhysicalLocationSerializer(serializers.ModelSerializer):
    """Flat serializer for PhysicalLocation with children count."""

    children_count = serializers.SerializerMethodField()

    class Meta:
        model = PhysicalLocation
        fields = [
            "id",
            "name",
            "location_type",
            "parent",
            "barcode",
            "capacity",
            "current_count",
            "notes",
            "is_active",
            "children_count",
        ]
        read_only_fields = ["id", "current_count"]

    def get_children_count(self, obj):
        return obj.get_children().count()


class PhysicalLocationTreeSerializer(serializers.ModelSerializer):
    """Recursive tree serializer for PhysicalLocation."""

    children = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = PhysicalLocation
        fields = [
            "id",
            "name",
            "location_type",
            "parent",
            "barcode",
            "capacity",
            "current_count",
            "notes",
            "is_active",
            "children_count",
            "children",
        ]
        read_only_fields = ["id", "current_count"]

    def get_children(self, obj):
        children = obj.get_children()
        return PhysicalLocationTreeSerializer(children, many=True).data

    def get_children_count(self, obj):
        return obj.get_children().count()


class PhysicalRecordSerializer(serializers.ModelSerializer):
    """Read serializer for PhysicalRecord with related names."""

    location_name = serializers.SerializerMethodField()
    document_title = serializers.SerializerMethodField()

    class Meta:
        model = PhysicalRecord
        fields = [
            "id",
            "document",
            "document_title",
            "location",
            "location_name",
            "position",
            "barcode",
            "condition",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "document_title",
            "location_name",
            "created_at",
            "updated_at",
        ]

    def get_location_name(self, obj):
        if obj.location:
            return str(obj.location)
        return ""

    def get_document_title(self, obj):
        return obj.document.title


class PhysicalRecordCreateSerializer(serializers.ModelSerializer):
    """Create/update serializer for PhysicalRecord."""

    class Meta:
        model = PhysicalRecord
        fields = [
            "id",
            "document",
            "location",
            "position",
            "barcode",
            "condition",
            "notes",
        ]
        read_only_fields = ["id"]


class ChargeOutSerializer(serializers.ModelSerializer):
    """Read serializer for ChargeOut with related names."""

    user_name = serializers.SerializerMethodField()
    record_barcode = serializers.SerializerMethodField()

    class Meta:
        model = ChargeOut
        fields = [
            "id",
            "physical_record",
            "user",
            "user_name",
            "record_barcode",
            "checked_out_at",
            "expected_return",
            "returned_at",
            "notes",
            "status",
        ]
        read_only_fields = [
            "id",
            "user_name",
            "record_barcode",
            "checked_out_at",
            "status",
        ]

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_record_barcode(self, obj):
        return obj.physical_record.barcode or ""


class ChargeOutCreateSerializer(serializers.Serializer):
    """Serializer for creating a new charge-out."""

    expected_return = serializers.DateTimeField()
    notes = serializers.CharField(required=False, default="", allow_blank=True)


class ChargeInSerializer(serializers.Serializer):
    """Serializer for returning (charging in) a physical record."""

    notes = serializers.CharField(required=False, default="", allow_blank=True)


class BarcodeCheckoutSerializer(serializers.Serializer):
    """Serializer for barcode-based checkout."""

    barcode = serializers.CharField(max_length=128)
    expected_return = serializers.DateTimeField()
    notes = serializers.CharField(required=False, default="", allow_blank=True)


class DestructionCertificateSerializer(serializers.ModelSerializer):
    """Read serializer for DestructionCertificate."""

    class Meta:
        model = DestructionCertificate
        fields = [
            "id",
            "physical_record",
            "destroyed_at",
            "destroyed_by",
            "method",
            "witness",
            "certificate_pdf",
            "notes",
        ]
        read_only_fields = ["id", "destroyed_at", "destroyed_by", "certificate_pdf"]


class DestructionCertificateCreateSerializer(serializers.Serializer):
    """Serializer for generating a destruction certificate."""

    method = serializers.CharField(max_length=32)
    witness = serializers.CharField(
        max_length=256, required=False, default="", allow_blank=True
    )
    notes = serializers.CharField(required=False, default="", allow_blank=True)

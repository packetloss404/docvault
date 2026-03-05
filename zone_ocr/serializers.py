"""Serializers for the Zone OCR module."""

from rest_framework import serializers

from .models import ZoneOCRField, ZoneOCRResult, ZoneOCRTemplate


class ZoneOCRFieldSerializer(serializers.ModelSerializer):
    """Full serializer for ZoneOCRField, used in nested template views."""

    class Meta:
        model = ZoneOCRField
        fields = [
            "id",
            "template",
            "name",
            "field_type",
            "bounding_box",
            "custom_field",
            "order",
            "preprocessing",
            "validation_regex",
        ]
        read_only_fields = ["id"]

    def validate_bounding_box(self, value):
        """Ensure bounding_box has the required keys and valid ranges."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Bounding box must be a JSON object.")

        required_keys = {"x", "y", "width", "height"}
        missing = required_keys - set(value.keys())
        if missing:
            raise serializers.ValidationError(
                f"Bounding box is missing keys: {', '.join(sorted(missing))}",
            )

        for key in required_keys:
            val = value[key]
            if not isinstance(val, (int, float)):
                raise serializers.ValidationError(
                    f"Bounding box key '{key}' must be a number.",
                )
            if val < 0 or val > 100:
                raise serializers.ValidationError(
                    f"Bounding box key '{key}' must be between 0 and 100.",
                )

        return value


class ZoneOCRTemplateSerializer(serializers.ModelSerializer):
    """Full serializer for ZoneOCRTemplate with nested fields."""

    fields = ZoneOCRFieldSerializer(many=True, read_only=True)
    field_count = serializers.SerializerMethodField()

    class Meta:
        model = ZoneOCRTemplate
        fields = [
            "id",
            "name",
            "description",
            "sample_page_image",
            "page_number",
            "is_active",
            "fields",
            "field_count",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]

    def get_field_count(self, obj):
        return obj.fields.count()


class ZoneOCRTemplateListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for template list views."""

    field_count = serializers.SerializerMethodField()

    class Meta:
        model = ZoneOCRTemplate
        fields = [
            "id",
            "name",
            "description",
            "page_number",
            "is_active",
            "field_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_field_count(self, obj):
        return obj.fields.count()


class ZoneOCRResultSerializer(serializers.ModelSerializer):
    """Full serializer for ZoneOCRResult with enriched read-only fields."""

    template_name = serializers.CharField(source="template.name", read_only=True)
    field_name = serializers.CharField(source="field.name", read_only=True)
    effective_value = serializers.CharField(read_only=True)

    class Meta:
        model = ZoneOCRResult
        fields = [
            "id",
            "document",
            "template",
            "template_name",
            "field",
            "field_name",
            "extracted_value",
            "confidence",
            "reviewed",
            "reviewed_by",
            "corrected_value",
            "effective_value",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "document",
            "template",
            "template_name",
            "field",
            "field_name",
            "extracted_value",
            "confidence",
            "reviewed_by",
            "created_at",
            "effective_value",
        ]


class ZoneOCRResultCorrectionSerializer(serializers.ModelSerializer):
    """Serializer for PATCH corrections on ZoneOCRResult."""

    class Meta:
        model = ZoneOCRResult
        fields = [
            "id",
            "corrected_value",
            "reviewed",
        ]
        read_only_fields = ["id"]


class TestTemplateSerializer(serializers.Serializer):
    """Serializer for the test-template endpoint (POST body)."""

    document_id = serializers.IntegerField(
        help_text="ID of the document to run zone OCR against.",
    )

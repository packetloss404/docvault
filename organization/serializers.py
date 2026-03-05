"""Serializers for the organization module."""

from rest_framework import serializers

from .models import (
    Cabinet,
    Correspondent,
    CustomField,
    CustomFieldInstance,
    DocumentMetadata,
    DocumentTypeCustomField,
    DocumentTypeMetadata,
    MetadataType,
    StoragePath,
    Tag,
)


class TagSerializer(serializers.ModelSerializer):
    """Full serializer for Tag with children count."""

    document_count = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = [
            "id", "name", "slug", "color", "is_inbox_tag",
            "parent",
            "match", "matching_algorithm", "is_insensitive",
            "document_count", "children_count",
            "owner",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "owner", "created_at", "updated_at"]

    def get_document_count(self, obj):
        return obj.documents.count()

    def get_children_count(self, obj):
        return obj.get_children().count()


class TagTreeSerializer(serializers.ModelSerializer):
    """Recursive serializer for Tag hierarchy."""

    children = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = [
            "id", "name", "slug", "color", "is_inbox_tag",
            "parent", "children",
            "document_count",
        ]

    def get_children(self, obj):
        children = obj.get_children()
        return TagTreeSerializer(children, many=True).data

    def get_document_count(self, obj):
        return obj.documents.count()


class CorrespondentSerializer(serializers.ModelSerializer):
    """Serializer for Correspondent."""

    document_count = serializers.SerializerMethodField()

    class Meta:
        model = Correspondent
        fields = [
            "id", "name", "slug",
            "match", "matching_algorithm", "is_insensitive",
            "document_count",
            "owner",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "owner", "created_at", "updated_at"]

    def get_document_count(self, obj):
        return obj.documents.count()


class CabinetSerializer(serializers.ModelSerializer):
    """Full serializer for Cabinet."""

    document_count = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = Cabinet
        fields = [
            "id", "name", "slug", "parent",
            "document_count", "children_count",
            "owner",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "owner", "created_at", "updated_at"]

    def get_document_count(self, obj):
        return obj.documents.count()

    def get_children_count(self, obj):
        return obj.get_children().count()


class CabinetTreeSerializer(serializers.ModelSerializer):
    """Recursive serializer for Cabinet hierarchy."""

    children = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()

    class Meta:
        model = Cabinet
        fields = [
            "id", "name", "slug", "parent", "children",
            "document_count",
        ]

    def get_children(self, obj):
        children = obj.get_children()
        return CabinetTreeSerializer(children, many=True).data

    def get_document_count(self, obj):
        return obj.documents.count()


class StoragePathSerializer(serializers.ModelSerializer):
    """Serializer for StoragePath."""

    document_count = serializers.SerializerMethodField()

    class Meta:
        model = StoragePath
        fields = [
            "id", "name", "slug", "path",
            "match", "matching_algorithm", "is_insensitive",
            "document_count",
            "owner",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "owner", "created_at", "updated_at"]

    def get_document_count(self, obj):
        return obj.documents.count()


class CustomFieldSerializer(serializers.ModelSerializer):
    """Serializer for CustomField definitions."""

    instance_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomField
        fields = [
            "id", "name", "slug", "data_type", "extra_data",
            "instance_count",
            "owner",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "owner", "created_at", "updated_at"]

    def get_instance_count(self, obj):
        return obj.instances.count()


class CustomFieldInstanceSerializer(serializers.ModelSerializer):
    """Serializer for per-document custom field values."""

    field_name = serializers.CharField(source="field.name", read_only=True)
    field_data_type = serializers.CharField(source="field.data_type", read_only=True)
    value = serializers.SerializerMethodField()

    class Meta:
        model = CustomFieldInstance
        fields = [
            "id", "document", "field", "field_name", "field_data_type",
            "value",
            "value_text", "value_bool", "value_url",
            "value_date", "value_datetime",
            "value_int", "value_float", "value_monetary",
            "value_document_ids", "value_select",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_value(self, obj):
        return obj.value


class CustomFieldInstanceWriteSerializer(serializers.ModelSerializer):
    """Write serializer for custom field instances - accepts 'value' field."""

    value = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = CustomFieldInstance
        fields = [
            "id", "document", "field", "value",
            "value_text", "value_bool", "value_url",
            "value_date", "value_datetime",
            "value_int", "value_float", "value_monetary",
            "value_document_ids", "value_select",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        value = validated_data.pop("value", None)
        instance = CustomFieldInstance(**validated_data)
        if value is not None:
            instance.value = value
        instance.save()
        return instance

    def update(self, instance, validated_data):
        value = validated_data.pop("value", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        if value is not None:
            instance.value = value
        instance.save()
        return instance


class DocumentTypeCustomFieldSerializer(serializers.ModelSerializer):
    """Serializer for DocumentType -> CustomField assignments."""

    field_name = serializers.CharField(source="custom_field.name", read_only=True)
    field_data_type = serializers.CharField(
        source="custom_field.data_type", read_only=True,
    )

    class Meta:
        model = DocumentTypeCustomField
        fields = [
            "id", "document_type", "custom_field",
            "field_name", "field_data_type",
            "required",
        ]
        read_only_fields = ["id"]


class MetadataTypeSerializer(serializers.ModelSerializer):
    """Serializer for MetadataType definitions."""

    instance_count = serializers.SerializerMethodField()

    class Meta:
        model = MetadataType
        fields = [
            "id", "name", "slug", "label",
            "default", "lookup", "validation", "parser",
            "instance_count",
            "owner",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "owner", "created_at", "updated_at"]

    def get_instance_count(self, obj):
        return obj.instances.count()


class DocumentMetadataSerializer(serializers.ModelSerializer):
    """Serializer for per-document metadata values."""

    metadata_type_name = serializers.CharField(
        source="metadata_type.name", read_only=True,
    )
    metadata_type_label = serializers.CharField(
        source="metadata_type.get_display_label", read_only=True,
    )
    parsed_value = serializers.SerializerMethodField()

    class Meta:
        model = DocumentMetadata
        fields = [
            "id", "document", "metadata_type",
            "metadata_type_name", "metadata_type_label",
            "value", "parsed_value",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_parsed_value(self, obj):
        parsed = obj.parsed_value
        # Ensure JSON-serializable
        if hasattr(parsed, "isoformat"):
            return parsed.isoformat()
        return parsed


class DocumentTypeMetadataSerializer(serializers.ModelSerializer):
    """Serializer for DocumentType -> MetadataType assignments."""

    metadata_type_name = serializers.CharField(
        source="metadata_type.name", read_only=True,
    )

    class Meta:
        model = DocumentTypeMetadata
        fields = [
            "id", "document_type", "metadata_type",
            "metadata_type_name",
            "required",
        ]
        read_only_fields = ["id"]


class BulkSetCustomFieldsSerializer(serializers.Serializer):
    """Serializer for bulk setting custom fields on multiple documents."""

    document_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
    )
    field_id = serializers.IntegerField()
    value = serializers.JSONField()


class BulkAssignSerializer(serializers.Serializer):
    """Serializer for bulk tag/correspondent assignment."""

    document_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
    )
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=[],
    )
    remove_tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=[],
    )
    correspondent_id = serializers.IntegerField(required=False, allow_null=True)
    cabinet_id = serializers.IntegerField(required=False, allow_null=True)

"""Serializers for the documents module."""

from rest_framework import serializers

from .models import Document, DocumentFile, DocumentType, DocumentVersion


class DocumentTypeSerializer(serializers.ModelSerializer):
    """Serializer for DocumentType with document count."""

    document_count = serializers.SerializerMethodField()

    class Meta:
        model = DocumentType
        fields = [
            "id", "name", "slug",
            "trash_time_period", "trash_time_unit",
            "delete_time_period", "delete_time_unit",
            "match", "matching_algorithm", "is_insensitive",
            "document_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]

    def get_document_count(self, obj):
        return obj.documents.count()


class DocumentFileSerializer(serializers.ModelSerializer):
    """Serializer for DocumentFile (nested in Document)."""

    class Meta:
        model = DocumentFile
        fields = [
            "id", "filename", "mime_type", "encoding",
            "checksum", "size", "comment", "created_at",
        ]
        read_only_fields = ["id", "checksum", "size", "created_at"]


class DocumentVersionSerializer(serializers.ModelSerializer):
    """Serializer for DocumentVersion (nested in Document)."""

    class Meta:
        model = DocumentVersion
        fields = [
            "id", "version_number", "comment",
            "is_active", "file", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class DocumentSerializer(serializers.ModelSerializer):
    """Full serializer for Document with nested relations."""

    document_type_name = serializers.StringRelatedField(
        source="document_type", read_only=True,
    )
    correspondent_name = serializers.StringRelatedField(
        source="correspondent", read_only=True,
    )
    cabinet_name = serializers.StringRelatedField(
        source="cabinet", read_only=True,
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        source="tags",
        many=True,
        read_only=True,
    )

    class Meta:
        model = Document
        fields = [
            "id", "uuid", "title", "content",
            "document_type", "document_type_name",
            "correspondent", "correspondent_name",
            "cabinet", "cabinet_name",
            "storage_path",
            "tag_ids",
            "original_filename", "mime_type", "checksum",
            "archive_checksum", "page_count",
            "filename", "archive_filename", "thumbnail_path",
            "created", "added",
            "archive_serial_number", "language",
            "owner",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "uuid", "checksum", "archive_checksum",
            "thumbnail_path",
            "owner", "created_at", "updated_at",
        ]


class DocumentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Document list endpoints."""

    document_type_name = serializers.StringRelatedField(
        source="document_type", read_only=True,
    )
    correspondent_name = serializers.StringRelatedField(
        source="correspondent", read_only=True,
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        source="tags",
        many=True,
        read_only=True,
    )

    class Meta:
        model = Document
        fields = [
            "id", "uuid", "title",
            "document_type", "document_type_name",
            "correspondent", "correspondent_name",
            "cabinet",
            "tag_ids",
            "original_filename", "mime_type",
            "page_count", "created", "added",
            "archive_serial_number", "language",
            "owner",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "uuid", "owner", "created_at", "updated_at",
        ]

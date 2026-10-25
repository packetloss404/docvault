"""Serializers for the documents module."""

from rest_framework import serializers

from .downloads import active_original, open_document_file
from .models import Document, DocumentFile, DocumentType, DocumentVersion


class ActiveVersionSerializer(serializers.ModelSerializer):
    mime_type = serializers.SerializerMethodField()
    original_filename = serializers.SerializerMethodField()
    page_count = serializers.SerializerMethodField()
    filename = serializers.SerializerMethodField()
    archive_filename = serializers.SerializerMethodField()
    checksum = serializers.SerializerMethodField()
    archive_checksum = serializers.SerializerMethodField()

    def _active_file(self, document):
        if not hasattr(document, "_serialized_active_file"):
            document._serialized_active_file = active_original(document)
        return document._serialized_active_file

    def get_mime_type(self, document) -> str:
        artifact = self._active_file(document)
        return artifact.mime_type if artifact else document.mime_type

    def get_original_filename(self, document) -> str:
        artifact = self._active_file(document)
        return artifact.filename if artifact else document.original_filename

    def get_filename(self, document) -> str:
        artifact = self._active_file(document)
        return artifact.file.name if artifact else document.filename or ""

    def get_checksum(self, document) -> str:
        artifact = self._active_file(document)
        return artifact.checksum if artifact else document.checksum

    def get_archive_filename(self, document) -> str:
        artifact = self._active_file(document)
        if artifact and artifact.file.name != document.filename:
            return ""
        return document.archive_filename or ""

    def get_archive_checksum(self, document) -> str:
        return document.archive_checksum if self.get_archive_filename(document) else ""

    def get_page_count(self, document) -> int:
        artifact = self._active_file(document)
        if not artifact or artifact.file.name == document.filename:
            return document.page_count
        if artifact.page_count:
            return artifact.page_count
        if artifact.mime_type.startswith("image/"):
            return 1
        if artifact.mime_type == "application/pdf":
            try:
                import pymupdf

                with open_document_file(artifact) as source, pymupdf.open(stream=source.read(), filetype="pdf") as pdf:
                    return len(pdf)
            except (OSError, RuntimeError, ValueError):
                return 0
        return 0


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

    def get_document_count(self, obj) -> int:
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


class DocumentSerializer(ActiveVersionSerializer):
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
            "is_held", "is_obsolete",
            "owner",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "uuid", "checksum", "archive_checksum",
            "filename", "archive_filename", "thumbnail_path",
            "original_filename", "mime_type", "page_count",
            "is_held", "is_obsolete",
            "owner", "created_at", "updated_at",
        ]


class DocumentListSerializer(ActiveVersionSerializer):
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
            "is_held", "is_obsolete",
            "owner",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "uuid", "owner", "created_at", "updated_at",
            "is_held", "is_obsolete",
        ]

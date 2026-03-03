"""Serializers for the contributor portal."""

from rest_framework import serializers

from .constants import SUBMISSION_APPROVED, SUBMISSION_REJECTED
from .models import DocumentRequest, PortalConfig, PortalSubmission


# ---------------------------------------------------------------------------
# Portal Configuration
# ---------------------------------------------------------------------------


class PortalConfigSerializer(serializers.ModelSerializer):
    """Full CRUD serializer for portal configurations (admin)."""

    class Meta:
        model = PortalConfig
        fields = [
            "id",
            "name",
            "slug",
            "welcome_text",
            "logo",
            "primary_color",
            "is_active",
            "require_email",
            "require_name",
            "default_document_type",
            "default_tags",
            "max_file_size_mb",
            "allowed_mime_types",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PortalConfigListSerializer(serializers.ModelSerializer):
    """Lightweight list serializer for portal configurations."""

    class Meta:
        model = PortalConfig
        fields = [
            "id",
            "name",
            "slug",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields


class PortalPublicSerializer(serializers.ModelSerializer):
    """Public-facing serializer (no sensitive/admin fields)."""

    class Meta:
        model = PortalConfig
        fields = [
            "name",
            "slug",
            "welcome_text",
            "logo",
            "primary_color",
            "require_email",
            "require_name",
            "allowed_mime_types",
            "max_file_size_mb",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Document Requests
# ---------------------------------------------------------------------------


class DocumentRequestSerializer(serializers.ModelSerializer):
    """Full CRUD serializer for document requests (admin)."""

    submission_count = serializers.SerializerMethodField()

    class Meta:
        model = DocumentRequest
        fields = [
            "id",
            "portal",
            "title",
            "description",
            "assignee_email",
            "assignee_name",
            "deadline",
            "token",
            "status",
            "sent_at",
            "reminder_sent_at",
            "submission_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "token",
            "sent_at",
            "reminder_sent_at",
            "submission_count",
            "created_at",
            "updated_at",
        ]

    def get_submission_count(self, obj):
        return obj.submissions.count()


class DocumentRequestListSerializer(serializers.ModelSerializer):
    """Lightweight list serializer for document requests."""

    portal_name = serializers.CharField(source="portal.name", read_only=True)

    class Meta:
        model = DocumentRequest
        fields = [
            "id",
            "portal",
            "portal_name",
            "title",
            "assignee_email",
            "deadline",
            "status",
            "created_at",
        ]
        read_only_fields = fields


class DocumentRequestPublicSerializer(serializers.ModelSerializer):
    """Public-facing serializer for document requests (via token)."""

    portal_name = serializers.CharField(source="portal.name", read_only=True)
    portal_welcome_text = serializers.CharField(
        source="portal.welcome_text", read_only=True,
    )
    portal_primary_color = serializers.CharField(
        source="portal.primary_color", read_only=True,
    )

    class Meta:
        model = DocumentRequest
        fields = [
            "title",
            "description",
            "deadline",
            "status",
            "portal_name",
            "portal_welcome_text",
            "portal_primary_color",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Portal Submissions
# ---------------------------------------------------------------------------


class PortalSubmissionSerializer(serializers.ModelSerializer):
    """Full serializer for admin review queue."""

    portal_name = serializers.CharField(source="portal.name", read_only=True)
    request_title = serializers.CharField(
        source="request.title", read_only=True, default=None,
    )
    reviewed_by_username = serializers.CharField(
        source="reviewed_by.username", read_only=True, default=None,
    )

    class Meta:
        model = PortalSubmission
        fields = [
            "id",
            "portal",
            "portal_name",
            "request",
            "request_title",
            "file",
            "original_filename",
            "submitter_email",
            "submitter_name",
            "metadata",
            "status",
            "reviewed_by",
            "reviewed_by_username",
            "reviewed_at",
            "review_notes",
            "ingested_document",
            "submitted_at",
            "ip_address",
        ]
        read_only_fields = fields


class PortalSubmissionListSerializer(serializers.ModelSerializer):
    """Lightweight list serializer for submissions."""

    portal_name = serializers.CharField(source="portal.name", read_only=True)

    class Meta:
        model = PortalSubmission
        fields = [
            "id",
            "portal",
            "portal_name",
            "original_filename",
            "submitter_email",
            "status",
            "submitted_at",
        ]
        read_only_fields = fields


class PublicUploadSerializer(serializers.Serializer):
    """Serializer for public file uploads."""

    file = serializers.FileField()
    email = serializers.EmailField(required=False, default="", allow_blank=True)
    name = serializers.CharField(
        required=False, default="", allow_blank=True, max_length=256,
    )
    metadata = serializers.JSONField(required=False, default=dict)


class SubmissionReviewSerializer(serializers.Serializer):
    """Serializer for approve/reject actions."""

    status = serializers.ChoiceField(
        choices=[SUBMISSION_APPROVED, SUBMISSION_REJECTED],
    )
    review_notes = serializers.CharField(
        required=False, default="", allow_blank=True,
    )

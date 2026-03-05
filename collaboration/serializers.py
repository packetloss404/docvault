"""Serializers for the collaboration module."""

from rest_framework import serializers

from .models import Checkout, Comment, ShareLink


class CommentSerializer(serializers.ModelSerializer):
    """Full serializer for Comment."""

    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Comment
        fields = [
            "id", "document", "user", "username", "text",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "document", "user", "username", "created_at", "updated_at"]


class CommentCreateSerializer(serializers.Serializer):
    """Serializer for creating a comment."""

    text = serializers.CharField(min_length=1)


class CheckoutSerializer(serializers.ModelSerializer):
    """Serializer for Checkout status."""

    username = serializers.CharField(source="user.username", read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Checkout
        fields = [
            "id", "document", "user", "username",
            "checked_out_at", "expiration", "block_new_uploads",
            "is_expired",
        ]
        read_only_fields = [
            "id", "document", "user", "username",
            "checked_out_at", "is_expired",
        ]


class CheckoutRequestSerializer(serializers.Serializer):
    """Serializer for checkout request."""

    expiration_hours = serializers.IntegerField(
        required=False, default=24, min_value=1, max_value=720,
    )
    block_new_uploads = serializers.BooleanField(required=False, default=True)


class ShareLinkSerializer(serializers.ModelSerializer):
    """Full serializer for ShareLink."""

    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True,
    )
    has_password = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    document_title = serializers.CharField(
        source="document.title", read_only=True,
    )

    class Meta:
        model = ShareLink
        fields = [
            "id", "document", "document_title", "slug",
            "created_by", "created_by_username",
            "expiration", "has_password", "is_expired",
            "file_version", "download_count",
            "created_at",
        ]
        read_only_fields = [
            "id", "slug", "created_by", "created_by_username",
            "download_count", "created_at", "document_title",
        ]


class ShareLinkCreateSerializer(serializers.Serializer):
    """Serializer for creating a share link."""

    expiration_hours = serializers.IntegerField(
        required=False, default=None, allow_null=True,
        min_value=1, max_value=8760,
    )
    password = serializers.CharField(required=False, default="", allow_blank=True)
    file_version = serializers.ChoiceField(
        choices=["original", "archive"],
        required=False,
        default="original",
    )


class ShareLinkAccessSerializer(serializers.Serializer):
    """Serializer for accessing a password-protected share link."""

    password = serializers.CharField(required=True)


class ActivityEntrySerializer(serializers.Serializer):
    """Serializer for activity feed entries."""

    id = serializers.IntegerField()
    event_type = serializers.CharField()
    title = serializers.CharField()
    body = serializers.CharField()
    document_id = serializers.IntegerField(allow_null=True)
    document_title = serializers.CharField(allow_null=True)
    user = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()

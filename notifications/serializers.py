"""Serializers for the notifications module."""

from rest_framework import serializers

from .models import Notification, NotificationPreference, Quota


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications."""

    class Meta:
        model = Notification
        fields = [
            "id",
            "event_type",
            "title",
            "body",
            "document",
            "read",
            "created_at",
        ]
        read_only_fields = ["id", "event_type", "title", "body", "document", "created_at"]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences."""

    class Meta:
        model = NotificationPreference
        fields = [
            "id",
            "event_type",
            "channel",
            "enabled",
            "webhook_url",
        ]
        read_only_fields = ["id"]


class QuotaSerializer(serializers.ModelSerializer):
    """Serializer for quotas (admin-only CRUD)."""

    username = serializers.CharField(source="user.username", read_only=True, default=None)
    group_name = serializers.CharField(source="group.name", read_only=True, default=None)

    class Meta:
        model = Quota
        fields = [
            "id",
            "user",
            "username",
            "group",
            "group_name",
            "max_documents",
            "max_storage_bytes",
        ]


class QuotaUsageSerializer(serializers.Serializer):
    """Read-only serializer for current quota usage."""

    document_count = serializers.IntegerField()
    storage_bytes = serializers.IntegerField()
    max_documents = serializers.IntegerField(allow_null=True)
    max_storage_bytes = serializers.IntegerField(allow_null=True)
    documents_remaining = serializers.IntegerField(allow_null=True)
    storage_remaining = serializers.IntegerField(allow_null=True)

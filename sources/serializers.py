"""Serializers for the sources module."""

from rest_framework import serializers

from .models import MailAccount, MailRule, Source, WatchFolderSource


class SourceSerializer(serializers.ModelSerializer):
    """Serializer for Source with tag IDs."""

    tag_ids = serializers.PrimaryKeyRelatedField(
        source="tags",
        many=True,
        read_only=True,
    )

    class Meta:
        model = Source
        fields = [
            "id", "label", "enabled", "source_type",
            "document_type", "tag_ids", "owner",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class WatchFolderSourceSerializer(serializers.ModelSerializer):
    """Serializer for WatchFolderSource."""

    class Meta:
        model = WatchFolderSource
        fields = [
            "id", "source", "path", "polling_interval",
            "consumed_action", "consumed_directory",
        ]
        read_only_fields = ["id", "source"]


class MailAccountSerializer(serializers.ModelSerializer):
    """Serializer for MailAccount.

    The password field is write-only for security.
    OAuth tokens are excluded from the API entirely.
    """

    rule_count = serializers.SerializerMethodField()

    class Meta:
        model = MailAccount
        fields = [
            "id", "name", "enabled",
            "imap_server", "port", "security",
            "account_type", "username", "password",
            "rule_count",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def get_rule_count(self, obj):
        return obj.rules.count()


class MailRuleSerializer(serializers.ModelSerializer):
    """Serializer for MailRule."""

    tag_ids = serializers.PrimaryKeyRelatedField(
        source="tags",
        many=True,
        read_only=True,
    )

    class Meta:
        model = MailRule
        fields = [
            "id", "name", "enabled", "account",
            "folder", "filter_from", "filter_subject",
            "filter_body", "filter_attachment_filename",
            "maximum_age", "action",
            "document_type", "tag_ids", "owner",
            "processed_action", "processed_folder",
            "order",
        ]
        read_only_fields = ["id", "account"]

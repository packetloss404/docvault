"""DRF serializers for the legal_hold module."""

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from .models import (
    LegalHold,
    LegalHoldCriteria,
    LegalHoldCustodian,
    LegalHoldDocument,
)


class LegalHoldCriteriaSerializer(serializers.ModelSerializer):
    """Serializer for legal hold criteria."""

    class Meta:
        model = LegalHoldCriteria
        fields = ["id", "hold", "criteria_type", "value"]
        read_only_fields = ["id"]
        extra_kwargs = {
            "hold": {"required": False},
        }


class LegalHoldCustodianSerializer(serializers.ModelSerializer):
    """Serializer for legal hold custodians with read-only username."""

    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = LegalHoldCustodian
        fields = [
            "id",
            "hold",
            "user",
            "username",
            "notified_at",
            "acknowledged",
            "acknowledged_at",
            "notes",
        ]
        read_only_fields = [
            "id",
            "notified_at",
            "acknowledged",
            "acknowledged_at",
        ]


class LegalHoldDocumentSerializer(serializers.ModelSerializer):
    """Serializer for legal hold documents with read-only document title."""

    document_title = serializers.CharField(
        source="document.title", read_only=True
    )

    class Meta:
        model = LegalHoldDocument
        fields = [
            "id",
            "hold",
            "document",
            "document_title",
            "held_at",
            "released_at",
        ]
        read_only_fields = ["id", "held_at", "released_at"]


class LegalHoldSerializer(serializers.ModelSerializer):
    """Full serializer for LegalHold with nested counts."""

    criteria_count = serializers.SerializerMethodField()
    custodian_count = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()
    released_by_username = serializers.CharField(
        source="released_by.username", read_only=True, default=None
    )

    class Meta:
        model = LegalHold
        fields = [
            "id",
            "name",
            "matter_number",
            "description",
            "status",
            "activated_at",
            "released_at",
            "released_by",
            "released_by_username",
            "release_reason",
            "criteria_count",
            "custodian_count",
            "document_count",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]
        read_only_fields = [
            "id",
            "status",
            "activated_at",
            "released_at",
            "released_by",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]

    def get_criteria_count(self, obj) -> int:
        return obj.criteria.count()

    def get_custodian_count(self, obj) -> int:
        return obj.custodians.count()

    def get_document_count(self, obj) -> int:
        return obj.held_documents.count()


class LegalHoldListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for hold list endpoints."""

    document_count = serializers.SerializerMethodField()
    custodian_count = serializers.SerializerMethodField()

    class Meta:
        model = LegalHold
        fields = [
            "id",
            "name",
            "matter_number",
            "status",
            "activated_at",
            "released_at",
            "document_count",
            "custodian_count",
            "created_at",
        ]
        read_only_fields = fields

    def get_document_count(self, obj) -> int:
        return obj.held_documents.count()

    def get_custodian_count(self, obj) -> int:
        return obj.custodians.count()


class LegalHoldCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a legal hold with nested criteria."""

    criteria = LegalHoldCriteriaSerializer(many=True, required=False)
    custodian_ids = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), many=True, required=False, write_only=True,
    )

    class Meta:
        model = LegalHold
        fields = [
            "id",
            "name",
            "matter_number",
            "description",
            "criteria",
            "custodian_ids",
        ]
        read_only_fields = ["id"]

    @transaction.atomic
    def create(self, validated_data):
        criteria_data = validated_data.pop("criteria", [])
        custodians = validated_data.pop("custodian_ids", [])
        hold = LegalHold.objects.create(**validated_data)
        for criterion in criteria_data:
            LegalHoldCriteria.objects.create(hold=hold, **criterion)
        LegalHoldCustodian.objects.bulk_create([
            LegalHoldCustodian(hold=hold, user=user) for user in dict.fromkeys(custodians)
        ])
        return hold


class LegalHoldReleaseSerializer(serializers.Serializer):
    """Serializer for releasing a legal hold."""

    reason = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class CustodianAcknowledgeSerializer(serializers.Serializer):
    """Serializer for custodian acknowledgement (no fields required)."""

    pass

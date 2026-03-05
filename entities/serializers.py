"""Serializers for the entities app."""

from rest_framework import serializers

from .models import Entity, EntityType


class EntityTypeSerializer(serializers.ModelSerializer):
    """Full serializer for EntityType CRUD."""

    class Meta:
        model = EntityType
        fields = [
            "id",
            "name",
            "label",
            "color",
            "icon",
            "extraction_pattern",
            "enabled",
        ]
        read_only_fields = ["id"]


class EntitySerializer(serializers.ModelSerializer):
    """Serializer for individual Entity records."""

    entity_type_name = serializers.CharField(
        source="entity_type.name", read_only=True,
    )
    entity_type_color = serializers.CharField(
        source="entity_type.color", read_only=True,
    )

    class Meta:
        model = Entity
        fields = [
            "id",
            "document",
            "entity_type",
            "entity_type_name",
            "entity_type_color",
            "value",
            "raw_value",
            "confidence",
            "start_offset",
            "end_offset",
            "page_number",
        ]
        read_only_fields = ["id"]


class EntityAggregateSerializer(serializers.Serializer):
    """Aggregation serializer: entity value with document count."""

    value = serializers.CharField()
    entity_type_name = serializers.CharField()
    entity_type_color = serializers.CharField()
    document_count = serializers.IntegerField()

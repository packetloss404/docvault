"""Serializers for the relationships module."""

from rest_framework import serializers

from .models import DocumentRelationship, RelationshipType


class RelationshipTypeSerializer(serializers.ModelSerializer):
    """Full serializer for RelationshipType."""

    class Meta:
        model = RelationshipType
        fields = [
            "id",
            "slug",
            "label",
            "icon",
            "is_directional",
            "is_builtin",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_builtin", "created_at", "updated_at"]


class DocumentRelationshipSerializer(serializers.ModelSerializer):
    """Read serializer for DocumentRelationship with denormalized labels."""

    source_title = serializers.CharField(
        source="source_document.title", read_only=True,
    )
    target_title = serializers.CharField(
        source="target_document.title", read_only=True,
    )
    relationship_type_label = serializers.CharField(
        source="relationship_type.label", read_only=True,
    )
    relationship_type_icon = serializers.CharField(
        source="relationship_type.icon", read_only=True,
    )

    class Meta:
        model = DocumentRelationship
        fields = [
            "id",
            "source_document",
            "target_document",
            "relationship_type",
            "source_title",
            "target_title",
            "relationship_type_label",
            "relationship_type_icon",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "source_title",
            "target_title",
            "relationship_type_label",
            "relationship_type_icon",
            "created_at",
            "updated_at",
        ]


class DocumentRelationshipCreateSerializer(serializers.Serializer):
    """Write serializer for creating a relationship (source comes from URL)."""

    target_document = serializers.IntegerField()
    relationship_type = serializers.IntegerField()
    notes = serializers.CharField(required=False, default="", allow_blank=True)


class RelationshipGraphNodeSerializer(serializers.Serializer):
    """A node in the relationship graph."""

    id = serializers.IntegerField()
    title = serializers.CharField()
    document_type = serializers.CharField(allow_null=True)


class RelationshipGraphEdgeSerializer(serializers.Serializer):
    """An edge in the relationship graph."""

    source = serializers.IntegerField()
    target = serializers.IntegerField()
    type = serializers.CharField()
    label = serializers.CharField()


class RelationshipGraphSerializer(serializers.Serializer):
    """Top-level serializer for the graph endpoint."""

    nodes = RelationshipGraphNodeSerializer(many=True)
    edges = RelationshipGraphEdgeSerializer(many=True)

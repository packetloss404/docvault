"""Serializers for the annotations module."""

from rest_framework import serializers

from .models import Annotation, AnnotationReply


class AnnotationReplySerializer(serializers.ModelSerializer):
    """Read serializer for annotation replies."""

    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = AnnotationReply
        fields = [
            "id",
            "author_name",
            "text",
            "created_at",
        ]
        read_only_fields = ["id", "author_name", "created_at"]


class AnnotationSerializer(serializers.ModelSerializer):
    """Read serializer for annotations with nested replies."""

    author_name = serializers.CharField(source="author.username", read_only=True)
    replies = AnnotationReplySerializer(many=True, read_only=True)
    reply_count = serializers.IntegerField(source="replies.count", read_only=True)

    class Meta:
        model = Annotation
        fields = [
            "id",
            "document",
            "page",
            "annotation_type",
            "coordinates",
            "content",
            "color",
            "opacity",
            "author",
            "author_name",
            "is_private",
            "replies",
            "reply_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "document",
            "author",
            "author_name",
            "replies",
            "reply_count",
            "created_at",
            "updated_at",
        ]


class AnnotationCreateSerializer(serializers.Serializer):
    """Serializer for creating a new annotation."""

    page = serializers.IntegerField(min_value=1)
    annotation_type = serializers.ChoiceField(
        choices=[c[0] for c in Annotation._meta.get_field("annotation_type").choices],
    )
    coordinates = serializers.DictField(child=serializers.FloatField(), default=dict)
    content = serializers.CharField(required=False, default="", allow_blank=True)
    color = serializers.CharField(max_length=7, default="#FFFF00")
    opacity = serializers.FloatField(min_value=0.0, max_value=1.0, default=0.3)
    is_private = serializers.BooleanField(default=False)

    def validate_coordinates(self, value):
        """Ensure all coordinate values are between 0.0 and 1.0."""
        for key, val in value.items():
            if not isinstance(val, (int, float)):
                raise serializers.ValidationError(
                    f"Coordinate '{key}' must be a number."
                )
            if val < 0.0 or val > 1.0:
                raise serializers.ValidationError(
                    f"Coordinate '{key}' must be between 0.0 and 1.0, got {val}."
                )
        return value


class AnnotationUpdateSerializer(serializers.Serializer):
    """Serializer for patching an annotation."""

    coordinates = serializers.DictField(
        child=serializers.FloatField(), required=False,
    )
    content = serializers.CharField(required=False, allow_blank=True)
    color = serializers.CharField(max_length=7, required=False)
    opacity = serializers.FloatField(min_value=0.0, max_value=1.0, required=False)

    def validate_coordinates(self, value):
        """Ensure all coordinate values are between 0.0 and 1.0."""
        for key, val in value.items():
            if not isinstance(val, (int, float)):
                raise serializers.ValidationError(
                    f"Coordinate '{key}' must be a number."
                )
            if val < 0.0 or val > 1.0:
                raise serializers.ValidationError(
                    f"Coordinate '{key}' must be between 0.0 and 1.0, got {val}."
                )
        return value


class AnnotationReplyCreateSerializer(serializers.Serializer):
    """Serializer for creating an annotation reply."""

    text = serializers.CharField(min_length=1)


class AnnotationExportSerializer(serializers.Serializer):
    """Empty serializer for the export action."""

    pass

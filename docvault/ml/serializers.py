"""Serializers for the ML classification module."""

from rest_framework import serializers


class SuggestionItemSerializer(serializers.Serializer):
    """A single ML suggestion with confidence score."""

    id = serializers.IntegerField()
    confidence = serializers.FloatField()
    name = serializers.CharField(required=False)


class SuggestionsSerializer(serializers.Serializer):
    """ML suggestions for a document."""

    tags = SuggestionItemSerializer(many=True)
    correspondent = SuggestionItemSerializer(many=True)
    document_type = SuggestionItemSerializer(many=True)
    storage_path = SuggestionItemSerializer(many=True)


class ClassifierStatusSerializer(serializers.Serializer):
    """Status of the trained classifier."""

    available = serializers.BooleanField()
    format_version = serializers.IntegerField(required=False)
    tags_trained = serializers.BooleanField()
    correspondent_trained = serializers.BooleanField()
    document_type_trained = serializers.BooleanField()
    storage_path_trained = serializers.BooleanField()
    tags_data_hash = serializers.CharField(required=False, allow_blank=True)
    correspondent_data_hash = serializers.CharField(required=False, allow_blank=True)
    document_type_data_hash = serializers.CharField(required=False, allow_blank=True)
    storage_path_data_hash = serializers.CharField(required=False, allow_blank=True)

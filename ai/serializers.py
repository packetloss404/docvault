"""Serializers for AI module API."""

from rest_framework import serializers


class SemanticSearchSerializer(serializers.Serializer):
    query = serializers.CharField(required=True, min_length=2)
    k = serializers.IntegerField(required=False, default=10, min_value=1, max_value=50)


class ChatMessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["user", "assistant"])
    content = serializers.CharField()


class DocumentChatSerializer(serializers.Serializer):
    question = serializers.CharField(required=True, min_length=2)
    history = ChatMessageSerializer(many=True, required=False, default=[])


class GlobalChatSerializer(serializers.Serializer):
    question = serializers.CharField(required=True, min_length=2)
    history = ChatMessageSerializer(many=True, required=False, default=[])


class SemanticSearchResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    correspondent = serializers.CharField(allow_null=True)
    document_type = serializers.CharField(allow_null=True)
    tags = serializers.ListField(child=serializers.CharField())
    created = serializers.CharField(allow_null=True)
    score = serializers.FloatField()


class ChatResponseSerializer(serializers.Serializer):
    answer = serializers.CharField()
    sources = serializers.ListField()


class SummaryResponseSerializer(serializers.Serializer):
    summary = serializers.CharField(allow_null=True)
    error = serializers.CharField(required=False)


class EntityResponseSerializer(serializers.Serializer):
    entities = serializers.DictField(allow_null=True)
    error = serializers.CharField(required=False)


class TitleSuggestionSerializer(serializers.Serializer):
    suggested_title = serializers.CharField(allow_null=True)
    error = serializers.CharField(required=False)


class AIConfigSerializer(serializers.Serializer):
    llm_enabled = serializers.BooleanField()
    llm_provider = serializers.CharField()
    llm_model = serializers.CharField()
    embedding_model = serializers.CharField()
    vector_store_count = serializers.IntegerField()


class AIStatusSerializer(serializers.Serializer):
    llm_enabled = serializers.BooleanField()
    llm_provider = serializers.CharField()
    llm_model = serializers.CharField()
    embedding_model = serializers.CharField()
    vector_store_count = serializers.IntegerField()
    llm_available = serializers.BooleanField()

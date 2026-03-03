"""Serializers for saved views and search analytics."""

from rest_framework import serializers

from .models import (
    SavedView,
    SavedViewFilterRule,
    SearchCuration,
    SearchQuery,
    SearchSynonym,
)


class SavedViewFilterRuleSerializer(serializers.ModelSerializer):
    """Serializer for a filter rule within a saved view."""

    rule_type_display = serializers.CharField(
        source="get_rule_type_display", read_only=True,
    )

    class Meta:
        model = SavedViewFilterRule
        fields = ["id", "rule_type", "rule_type_display", "value"]
        read_only_fields = ["id"]


class SavedViewSerializer(serializers.ModelSerializer):
    """Serializer for SavedView with nested filter rules."""

    filter_rules = SavedViewFilterRuleSerializer(many=True, required=False)

    class Meta:
        model = SavedView
        fields = [
            "id", "name", "display_mode", "display_fields",
            "sort_field", "sort_reverse", "page_size",
            "show_on_dashboard", "show_in_sidebar",
            "filter_rules",
            "owner",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]

    def create(self, validated_data):
        rules_data = validated_data.pop("filter_rules", [])
        saved_view = SavedView.objects.create(**validated_data)
        for rule_data in rules_data:
            SavedViewFilterRule.objects.create(saved_view=saved_view, **rule_data)
        return saved_view

    def update(self, instance, validated_data):
        rules_data = validated_data.pop("filter_rules", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if rules_data is not None:
            # Replace all rules
            instance.filter_rules.all().delete()
            for rule_data in rules_data:
                SavedViewFilterRule.objects.create(
                    saved_view=instance, **rule_data,
                )

        return instance


class SavedViewListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing saved views."""

    rule_count = serializers.SerializerMethodField()

    class Meta:
        model = SavedView
        fields = [
            "id", "name", "display_mode",
            "show_on_dashboard", "show_in_sidebar",
            "rule_count",
            "owner",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]

    def get_rule_count(self, obj):
        return obj.filter_rules.count()


# ---------------------------------------------------------------------------
# Search analytics serializers (Sprint 19)
# ---------------------------------------------------------------------------


class SearchQuerySerializer(serializers.ModelSerializer):
    """Serializer for recorded search queries."""

    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = SearchQuery
        fields = [
            "id",
            "query_text",
            "user",
            "username",
            "results_count",
            "clicked_document",
            "click_position",
            "timestamp",
            "response_time_ms",
        ]
        read_only_fields = [
            "id",
            "user",
            "username",
            "timestamp",
        ]


class SearchSynonymSerializer(serializers.ModelSerializer):
    """Serializer for synonym groups."""

    class Meta:
        model = SearchSynonym
        fields = [
            "id",
            "terms",
            "enabled",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["id", "created_by", "created_at"]


class SearchCurationSerializer(serializers.ModelSerializer):
    """Serializer for curated search results."""

    class Meta:
        model = SearchCuration
        fields = [
            "id",
            "query_text",
            "pinned_documents",
            "hidden_documents",
            "boost_fields",
            "enabled",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["id", "created_by", "created_at"]


class SearchAnalyticsSerializer(serializers.Serializer):
    """Aggregated analytics data for the search dashboard."""

    top_queries = serializers.ListField(child=serializers.DictField())
    zero_result_queries = serializers.ListField(child=serializers.DictField())
    average_ctr = serializers.FloatField()
    query_volume = serializers.ListField(child=serializers.DictField())
    total_queries = serializers.IntegerField()
    total_clicks = serializers.IntegerField()

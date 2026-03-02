"""Serializers for the workflows module."""

from rest_framework import serializers

from .models import (
    WorkflowInstance,
    WorkflowInstanceLogEntry,
    WorkflowState,
    WorkflowStateAction,
    WorkflowStateEscalation,
    WorkflowTemplate,
    WorkflowTransition,
    WorkflowTransitionField,
)


class WorkflowTemplateSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowTemplate with computed counts."""

    state_count = serializers.SerializerMethodField()
    transition_count = serializers.SerializerMethodField()
    document_type_ids = serializers.PrimaryKeyRelatedField(
        source="document_types",
        many=True,
        read_only=True,
    )

    class Meta:
        model = WorkflowTemplate
        fields = [
            "id", "label", "internal_name", "auto_launch",
            "document_type_ids", "state_count", "transition_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "internal_name", "created_at", "updated_at"]

    def get_state_count(self, obj):
        return obj.states.count()

    def get_transition_count(self, obj):
        return obj.transitions.count()


class WorkflowStateSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowState."""

    class Meta:
        model = WorkflowState
        fields = [
            "id", "workflow", "label", "initial", "final", "completion",
        ]
        read_only_fields = ["id", "workflow"]


class WorkflowTransitionSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowTransition with state labels."""

    origin_state_label = serializers.CharField(
        source="origin_state.label", read_only=True,
    )
    destination_state_label = serializers.CharField(
        source="destination_state.label", read_only=True,
    )

    class Meta:
        model = WorkflowTransition
        fields = [
            "id", "workflow", "label",
            "origin_state", "origin_state_label",
            "destination_state", "destination_state_label",
            "condition",
        ]
        read_only_fields = ["id", "workflow"]


class WorkflowTransitionFieldSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowTransitionField."""

    class Meta:
        model = WorkflowTransitionField
        fields = [
            "id", "transition", "name", "label",
            "field_type", "required", "default", "help_text",
        ]
        read_only_fields = ["id", "transition"]


class WorkflowStateActionSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowStateAction."""

    class Meta:
        model = WorkflowStateAction
        fields = [
            "id", "state", "label", "enabled", "when",
            "backend_path", "backend_data", "condition", "order",
        ]
        read_only_fields = ["id", "state"]


class WorkflowStateEscalationSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowStateEscalation."""

    class Meta:
        model = WorkflowStateEscalation
        fields = [
            "id", "state", "transition", "enabled",
            "amount", "unit", "condition", "comment", "priority",
        ]
        read_only_fields = ["id", "state"]


class WorkflowInstanceLogEntrySerializer(serializers.ModelSerializer):
    """Serializer for WorkflowInstanceLogEntry."""

    transition_label = serializers.CharField(
        source="transition.label", read_only=True, default=None,
    )
    username = serializers.CharField(
        source="user.username", read_only=True, default=None,
    )

    class Meta:
        model = WorkflowInstanceLogEntry
        fields = [
            "id", "instance", "datetime",
            "transition", "transition_label",
            "user", "username",
            "comment", "transition_field_values",
        ]
        read_only_fields = ["id", "datetime"]


class WorkflowInstanceSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowInstance with computed properties."""

    workflow_label = serializers.CharField(
        source="workflow.label", read_only=True,
    )
    current_state_label = serializers.CharField(
        source="current_state.label", read_only=True, default=None,
    )
    is_complete = serializers.BooleanField(read_only=True)
    completion = serializers.IntegerField(
        source="current_state.completion", read_only=True, default=0,
    )

    class Meta:
        model = WorkflowInstance
        fields = [
            "id", "workflow", "workflow_label",
            "document", "current_state", "current_state_label",
            "completion", "is_complete",
            "context", "launched_at", "state_changed_at",
        ]
        read_only_fields = [
            "id", "launched_at", "state_changed_at",
        ]


class TransitionExecuteSerializer(serializers.Serializer):
    """Serializer for executing a transition."""

    field_values = serializers.DictField(
        child=serializers.CharField(allow_blank=True),
        required=False,
        default=dict,
    )
    comment = serializers.CharField(required=False, default="", allow_blank=True)

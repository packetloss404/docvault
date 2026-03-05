"""Serializers for the processing module."""

from rest_framework import serializers

from .models import ProcessingTask


class ProcessingTaskSerializer(serializers.ModelSerializer):
    """Serializer for ProcessingTask list and detail views."""

    class Meta:
        model = ProcessingTask
        fields = [
            "id", "task_id", "task_name", "status",
            "progress", "status_message", "result",
            "acknowledged", "document",
            "created_at", "started_at", "completed_at",
        ]
        read_only_fields = [
            "id", "task_id", "task_name", "status",
            "progress", "status_message", "result",
            "document", "created_at", "started_at", "completed_at",
        ]

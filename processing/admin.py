"""Admin configuration for the processing module."""

from django.contrib import admin

from .models import ProcessingTask


@admin.register(ProcessingTask)
class ProcessingTaskAdmin(admin.ModelAdmin):
    list_display = ["task_id", "task_name", "status", "progress", "owner", "created_at"]
    list_filter = ["status", "task_name"]
    search_fields = ["task_id", "task_name", "status_message"]
    readonly_fields = ["task_id", "created_at", "started_at", "completed_at"]

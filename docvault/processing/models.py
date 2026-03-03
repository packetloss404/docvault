"""Models for the processing module."""

import uuid

from django.conf import settings
from django.db import models


class ProcessingTask(models.Model):
    """Tracks the status and progress of async document processing tasks."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        STARTED = "started", "Started"
        SUCCESS = "success", "Success"
        FAILURE = "failure", "Failure"

    task_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    task_name = models.CharField(max_length=256, default="document_consumption")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    progress = models.FloatField(
        default=0.0,
        help_text="Progress from 0.0 to 1.0",
    )
    status_message = models.CharField(max_length=512, blank=True, default="")
    result = models.TextField(blank=True, default="")
    acknowledged = models.BooleanField(default=False)

    document = models.ForeignKey(
        "documents.Document",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="processing_tasks",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="processing_tasks",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "processing task"
        verbose_name_plural = "processing tasks"

    def __str__(self):
        return f"{self.task_name} [{self.status}] ({self.task_id})"

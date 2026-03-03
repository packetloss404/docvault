"""Views for the processing module."""

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import ProcessingTask
from .serializers import ProcessingTaskSerializer


class ProcessingTaskViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve processing tasks for the current user."""

    serializer_class = ProcessingTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return ProcessingTask.objects.all()
        return ProcessingTask.objects.filter(owner=user)

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        """Mark a task as acknowledged/seen by the user."""
        task = self.get_object()
        task.acknowledged = True
        task.save(update_fields=["acknowledged"])
        return Response(ProcessingTaskSerializer(task).data)

    @action(detail=False, methods=["get"])
    def pending(self, request):
        """List unacknowledged tasks for notification display."""
        qs = self.get_queryset().filter(acknowledged=False)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

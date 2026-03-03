"""API views for the notifications module."""

from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification, NotificationPreference, Quota
from .quotas import get_quota_usage_data
from .serializers import (
    NotificationPreferenceSerializer,
    NotificationSerializer,
    QuotaSerializer,
    QuotaUsageSerializer,
)


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user notifications.

    list: Returns paginated notifications for the authenticated user.
    read: Mark a single notification as read.
    read_all: Mark all notifications as read.
    """

    serializer_class = NotificationSerializer
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        # Optional filter: unread only
        unread = self.request.query_params.get("unread")
        if unread and unread.lower() in ("true", "1"):
            qs = qs.filter(read=False)
        return qs

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        """Mark a single notification as read."""
        notification = self.get_object()
        notification.read = True
        notification.save(update_fields=["read"])
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"])
    def read_all(self, request):
        """Mark all unread notifications as read."""
        count = Notification.objects.filter(
            user=request.user, read=False
        ).update(read=True)
        return Response({"marked_read": count})

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        """Return the count of unread notifications."""
        count = Notification.objects.filter(
            user=request.user, read=False
        ).count()
        return Response({"count": count})


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for notification preferences.

    Users can view and update their delivery preferences per
    event_type and channel.
    """

    serializer_class = NotificationPreferenceSerializer

    def get_queryset(self):
        return NotificationPreference.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class QuotaViewSet(viewsets.ModelViewSet):
    """Admin-only quota CRUD."""

    serializer_class = QuotaSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Quota.objects.all()


class QuotaUsageView(generics.GenericAPIView):
    """Return current quota usage for the authenticated user."""

    serializer_class = QuotaUsageSerializer

    def get(self, request):
        data = get_quota_usage_data(request.user)
        serializer = self.get_serializer(data)
        return Response(serializer.data)

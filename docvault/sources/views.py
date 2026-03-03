"""Views for the sources module."""

import logging

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from security.permissions import IsAdminOrReadOnly

from .mail import test_connection
from .models import MailAccount, MailRule, Source, WatchFolderSource
from .serializers import (
    MailAccountSerializer,
    MailRuleSerializer,
    SourceSerializer,
    WatchFolderSourceSerializer,
)

logger = logging.getLogger(__name__)


class SourceViewSet(viewsets.ModelViewSet):
    """CRUD for document sources."""

    queryset = Source.objects.all()
    serializer_class = SourceSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    search_fields = ["label"]
    ordering_fields = ["label", "created_at"]
    ordering = ["label"]

    @action(
        detail=True,
        methods=["get", "post", "patch"],
        url_path="watch-folder",
    )
    def watch_folder(self, request, pk=None):
        """Get or create/update the watch folder config for a source."""
        source = self.get_object()

        if request.method == "GET":
            try:
                wf = source.watch_folder
            except WatchFolderSource.DoesNotExist:
                return Response(
                    {"error": "No watch folder configuration for this source."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(WatchFolderSourceSerializer(wf).data)

        # POST or PATCH
        try:
            wf = source.watch_folder
            serializer = WatchFolderSourceSerializer(
                wf, data=request.data, partial=True,
            )
        except WatchFolderSource.DoesNotExist:
            serializer = WatchFolderSourceSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save(source=source)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
            if request.method == "POST"
            else status.HTTP_200_OK,
        )


class MailAccountViewSet(viewsets.ModelViewSet):
    """CRUD for mail accounts."""

    queryset = MailAccount.objects.all()
    serializer_class = MailAccountSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    search_fields = ["name", "username"]
    ordering = ["name"]

    @action(detail=True, methods=["post"], url_path="test-connection")
    def test_connection(self, request, pk=None):
        """Test IMAP connection for a mail account."""
        account = self.get_object()
        success, message = test_connection(account)
        return Response({"success": success, "message": message})


class MailRuleViewSet(viewsets.ModelViewSet):
    """CRUD for mail rules within a mail account."""

    serializer_class = MailRuleSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        return MailRule.objects.filter(
            account_id=self.kwargs["account_pk"],
        )

    def perform_create(self, serializer):
        serializer.save(account_id=self.kwargs["account_pk"])

"""API views for collaboration features."""

import logging
from datetime import timedelta

from django.http import Http404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.models import Document

from .models import Checkout, Comment, ShareLink
from .serializers import (
    ActivityEntrySerializer,
    CheckoutRequestSerializer,
    CheckoutSerializer,
    CommentCreateSerializer,
    CommentSerializer,
    ShareLinkCreateSerializer,
    ShareLinkSerializer,
)

logger = logging.getLogger(__name__)


# --- Comments ---


class DocumentCommentListView(APIView):
    """GET/POST /api/v1/documents/{id}/comments/"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        comments = Comment.objects.filter(document_id=pk).select_related("user")
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        try:
            document = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            raise Http404("Document not found.")

        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = Comment.objects.create(
            document=document,
            user=request.user,
            text=serializer.validated_data["text"],
            created_by=request.user,
        )

        return Response(
            CommentSerializer(comment).data,
            status=status.HTTP_201_CREATED,
        )


class DocumentCommentDetailView(APIView):
    """PATCH/DELETE /api/v1/documents/{id}/comments/{cid}/"""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk, cid):
        try:
            comment = Comment.objects.get(pk=cid, document_id=pk)
        except Comment.DoesNotExist:
            raise Http404("Comment not found.")

        if comment.user != request.user and not request.user.is_superuser:
            return Response(
                {"error": "You can only edit your own comments."},
                status=status.HTTP_403_FORBIDDEN,
            )

        text = request.data.get("text")
        if text:
            comment.text = text
            comment.save(update_fields=["text", "updated_at"])

        return Response(CommentSerializer(comment).data)

    def delete(self, request, pk, cid):
        try:
            comment = Comment.objects.get(pk=cid, document_id=pk)
        except Comment.DoesNotExist:
            raise Http404("Comment not found.")

        if comment.user != request.user and not request.user.is_superuser:
            return Response(
                {"error": "You can only delete your own comments."},
                status=status.HTTP_403_FORBIDDEN,
            )

        comment.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Check-in / Check-out ---


class DocumentCheckoutView(APIView):
    """POST /api/v1/documents/{id}/checkout/ — Lock the document."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            document = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            raise Http404("Document not found.")

        if hasattr(document, "checkout"):
            existing = document.checkout
            if not existing.is_expired:
                return Response(
                    {
                        "error": "Document is already checked out.",
                        "checked_out_by": existing.user.username,
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            # Expired checkout — release it
            existing.delete()

        serializer = CheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        hours = serializer.validated_data["expiration_hours"]
        expiration = timezone.now() + timedelta(hours=hours)

        checkout = Checkout.objects.create(
            document=document,
            user=request.user,
            expiration=expiration,
            block_new_uploads=serializer.validated_data["block_new_uploads"],
        )

        return Response(
            CheckoutSerializer(checkout).data,
            status=status.HTTP_201_CREATED,
        )


class DocumentCheckinView(APIView):
    """POST /api/v1/documents/{id}/checkin/ — Unlock the document."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            document = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            raise Http404("Document not found.")

        try:
            checkout = document.checkout
        except Checkout.DoesNotExist:
            return Response(
                {"error": "Document is not checked out."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Only the checker-outer, doc owner, or admin can check in
        if (
            checkout.user != request.user
            and document.owner != request.user
            and not request.user.is_superuser
        ):
            return Response(
                {"error": "You do not have permission to check in this document."},
                status=status.HTTP_403_FORBIDDEN,
            )

        checkout.delete()
        return Response({"status": "checked_in"})


class DocumentCheckoutStatusView(APIView):
    """GET /api/v1/documents/{id}/checkout_status/"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            document = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            raise Http404("Document not found.")

        try:
            checkout = document.checkout
        except Checkout.DoesNotExist:
            return Response({"checked_out": False})

        if checkout.is_expired:
            checkout.delete()
            return Response({"checked_out": False})

        return Response({
            "checked_out": True,
            "checkout": CheckoutSerializer(checkout).data,
        })


# --- Share Links ---


class DocumentShareCreateView(APIView):
    """POST /api/v1/documents/{id}/share/ — Create a share link."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            document = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            raise Http404("Document not found.")

        serializer = ShareLinkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        link = ShareLink(
            document=document,
            created_by=request.user,
            file_version=serializer.validated_data["file_version"],
        )

        hours = serializer.validated_data.get("expiration_hours")
        if hours:
            link.expiration = timezone.now() + timedelta(hours=hours)

        password = serializer.validated_data.get("password", "")
        if password:
            link.set_password(password)

        link.save()

        return Response(
            ShareLinkSerializer(link).data,
            status=status.HTTP_201_CREATED,
        )


class ShareLinkListView(APIView):
    """GET /api/v1/share-links/ — List current user's share links."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        links = ShareLink.objects.filter(
            created_by=request.user,
        ).select_related("document")
        serializer = ShareLinkSerializer(links, many=True)
        return Response(serializer.data)


class ShareLinkDeleteView(APIView):
    """DELETE /api/v1/share-links/{id}/ — Revoke a share link."""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        try:
            link = ShareLink.objects.get(pk=pk, created_by=request.user)
        except ShareLink.DoesNotExist:
            raise Http404("Share link not found.")

        link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicShareAccessView(APIView):
    """GET /api/v1/share/{slug}/ — Public access to a shared document (no auth)."""

    permission_classes = []
    authentication_classes = []

    def get(self, request, slug):
        try:
            link = ShareLink.objects.select_related("document").get(slug=slug)
        except ShareLink.DoesNotExist:
            raise Http404("Share link not found.")

        if link.is_expired:
            raise Http404("This share link has expired.")

        if link.has_password:
            return Response({
                "requires_password": True,
                "document_title": link.document.title,
            })

        link.download_count += 1
        link.save(update_fields=["download_count"])

        return Response({
            "document_id": link.document.pk,
            "document_title": link.document.title,
            "file_version": link.file_version,
            "download_count": link.download_count,
        })

    def post(self, request, slug):
        """Verify password for a password-protected share link."""
        try:
            link = ShareLink.objects.select_related("document").get(slug=slug)
        except ShareLink.DoesNotExist:
            raise Http404("Share link not found.")

        if link.is_expired:
            raise Http404("This share link has expired.")

        password = request.data.get("password", "")
        if not link.check_password(password):
            return Response(
                {"error": "Invalid password."},
                status=status.HTTP_403_FORBIDDEN,
            )

        link.download_count += 1
        link.save(update_fields=["download_count"])

        return Response({
            "document_id": link.document.pk,
            "document_title": link.document.title,
            "file_version": link.file_version,
            "download_count": link.download_count,
        })


# --- Activity Feed ---


class DocumentActivityView(APIView):
    """GET /api/v1/documents/{id}/activity/ — Per-document activity timeline."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            document = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            raise Http404("Document not found.")

        from notifications.models import Notification

        notifications = Notification.objects.filter(
            document=document,
        ).select_related("user").order_by("-created_at")[:50]

        entries = []
        for n in notifications:
            entries.append({
                "id": n.pk,
                "event_type": n.event_type,
                "title": n.title,
                "body": n.body,
                "document_id": document.pk,
                "document_title": document.title,
                "user": n.user.username if n.user else None,
                "created_at": n.created_at,
            })

        return Response(entries)


class GlobalActivityView(APIView):
    """GET /api/v1/activity/ — Global activity feed (permission-filtered)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from notifications.models import Notification

        qs = Notification.objects.select_related(
            "user", "document",
        ).order_by("-created_at")

        if not request.user.is_superuser:
            qs = qs.filter(user=request.user)

        notifications = qs[:100]

        entries = []
        for n in notifications:
            entries.append({
                "id": n.pk,
                "event_type": n.event_type,
                "title": n.title,
                "body": n.body,
                "document_id": n.document_id,
                "document_title": n.document.title if n.document else None,
                "user": n.user.username if n.user else None,
                "created_at": n.created_at,
            })

        return Response(entries)

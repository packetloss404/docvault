"""API views for the annotations module."""

import logging

from django.db.models import Q
from django.http import Http404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from documents.models import Document

from .models import Annotation, AnnotationReply
from .serializers import (
    AnnotationCreateSerializer,
    AnnotationExportSerializer,
    AnnotationReplyCreateSerializer,
    AnnotationReplySerializer,
    AnnotationSerializer,
    AnnotationUpdateSerializer,
)

logger = logging.getLogger(__name__)


class DocumentAnnotationViewSet(ViewSet):
    """
    ViewSet for managing annotations on a document.

    list:   GET  /documents/{document_id}/annotations/
    create: POST /documents/{document_id}/annotations/
    retrieve: GET  /documents/{document_id}/annotations/{pk}/
    partial_update: PATCH /documents/{document_id}/annotations/{pk}/
    destroy: DELETE /documents/{document_id}/annotations/{pk}/
    export: POST /documents/{document_id}/annotations/export/
    """

    permission_classes = [permissions.IsAuthenticated]

    def _get_document(self, document_id):
        try:
            return Document.objects.get(pk=document_id)
        except Document.DoesNotExist:
            raise Http404("Document not found.")

    def _filter_private(self, queryset, user):
        """Filter out private annotations unless the user is the author or staff."""
        if user.is_staff:
            return queryset
        return queryset.filter(Q(is_private=False) | Q(is_private=True, author=user))

    def list(self, request, document_id):
        self._get_document(document_id)

        qs = Annotation.objects.filter(
            document_id=document_id,
        ).select_related("author").prefetch_related("replies", "replies__author")

        # Optional filters
        page = request.query_params.get("page")
        if page is not None:
            qs = qs.filter(page=page)

        annotation_type = request.query_params.get("type")
        if annotation_type:
            qs = qs.filter(annotation_type=annotation_type)

        author_id = request.query_params.get("author")
        if author_id:
            qs = qs.filter(author_id=author_id)

        qs = self._filter_private(qs, request.user)

        serializer = AnnotationSerializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request, document_id):
        document = self._get_document(document_id)

        serializer = AnnotationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        annotation = Annotation.objects.create(
            document=document,
            author=request.user,
            created_by=request.user,
            **serializer.validated_data,
        )

        return Response(
            AnnotationSerializer(annotation).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, document_id, pk):
        self._get_document(document_id)

        try:
            annotation = Annotation.objects.select_related("author").prefetch_related(
                "replies", "replies__author",
            ).get(pk=pk, document_id=document_id)
        except Annotation.DoesNotExist:
            raise Http404("Annotation not found.")

        # Private check
        if annotation.is_private and annotation.author != request.user and not request.user.is_staff:
            raise Http404("Annotation not found.")

        serializer = AnnotationSerializer(annotation)
        return Response(serializer.data)

    def partial_update(self, request, document_id, pk):
        document = self._get_document(document_id)

        try:
            annotation = Annotation.objects.get(pk=pk, document_id=document_id)
        except Annotation.DoesNotExist:
            raise Http404("Annotation not found.")

        # Only the annotation author or the document owner can update
        if annotation.author != request.user and document.owner != request.user:
            return Response(
                {"error": "You do not have permission to update this annotation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AnnotationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        for field, value in serializer.validated_data.items():
            setattr(annotation, field, value)
        annotation.updated_by = request.user
        annotation.save()

        return Response(AnnotationSerializer(annotation).data)

    def destroy(self, request, document_id, pk):
        document = self._get_document(document_id)

        try:
            annotation = Annotation.objects.get(pk=pk, document_id=document_id)
        except Annotation.DoesNotExist:
            raise Http404("Annotation not found.")

        # Only the author, document owner, or admin can delete
        if (
            annotation.author != request.user
            and document.owner != request.user
            and not request.user.is_staff
        ):
            return Response(
                {"error": "You do not have permission to delete this annotation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        annotation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def export(self, request, document_id):
        """Export annotations as JSON for PDF overlay (stub)."""
        self._get_document(document_id)

        qs = Annotation.objects.filter(
            document_id=document_id,
        ).select_related("author").prefetch_related("replies", "replies__author")

        qs = self._filter_private(qs, request.user)

        serializer = AnnotationSerializer(qs, many=True)
        return Response({
            "document_id": document_id,
            "annotation_count": len(serializer.data),
            "annotations": serializer.data,
        })


class AnnotationReplyListCreateView(APIView):
    """
    GET/POST /documents/{document_id}/annotations/{annotation_id}/replies/
    """

    permission_classes = [permissions.IsAuthenticated]

    def _get_annotation(self, document_id, annotation_id, user):
        try:
            annotation = Annotation.objects.get(
                pk=annotation_id, document_id=document_id,
            )
        except Annotation.DoesNotExist:
            raise Http404("Annotation not found.")

        # Private annotation check
        if annotation.is_private and annotation.author != user and not user.is_staff:
            raise Http404("Annotation not found.")

        return annotation

    def get(self, request, document_id, annotation_id):
        annotation = self._get_annotation(document_id, annotation_id, request.user)
        replies = AnnotationReply.objects.filter(
            annotation=annotation,
        ).select_related("author")
        serializer = AnnotationReplySerializer(replies, many=True)
        return Response(serializer.data)

    def post(self, request, document_id, annotation_id):
        annotation = self._get_annotation(document_id, annotation_id, request.user)

        serializer = AnnotationReplyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reply = AnnotationReply.objects.create(
            annotation=annotation,
            author=request.user,
            text=serializer.validated_data["text"],
        )

        return Response(
            AnnotationReplySerializer(reply).data,
            status=status.HTTP_201_CREATED,
        )

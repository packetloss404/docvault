"""API views for the ML classification module."""

import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.models import Document

from .classifier import get_classifier
from .serializers import ClassifierStatusSerializer, SuggestionsSerializer
from .tasks import get_suggestions_for_document

logger = logging.getLogger(__name__)


class DocumentSuggestionsView(APIView):
    """GET /api/v1/documents/{id}/suggestions/

    Returns ML-based suggestions with confidence scores for a document.
    """

    def get(self, request, document_pk):
        try:
            document = Document.objects.get(pk=document_pk)
        except Document.DoesNotExist:
            return Response(
                {"error": "Document not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        suggestions = get_suggestions_for_document(document)

        # Enrich with names
        self._enrich_names(suggestions)

        serializer = SuggestionsSerializer(suggestions)
        return Response(serializer.data)

    def _enrich_names(self, suggestions):
        """Add human-readable names to suggestion IDs."""
        from documents.models.document_type import DocumentType
        from organization.models import Correspondent, StoragePath, Tag

        for item in suggestions.get("tags", []):
            try:
                item["name"] = Tag.objects.get(pk=item["id"]).name
            except Tag.DoesNotExist:
                item["name"] = f"Tag #{item['id']}"

        for item in suggestions.get("correspondent", []):
            try:
                item["name"] = Correspondent.objects.get(pk=item["id"]).name
            except Correspondent.DoesNotExist:
                item["name"] = f"Correspondent #{item['id']}"

        for item in suggestions.get("document_type", []):
            try:
                item["name"] = DocumentType.objects.get(pk=item["id"]).name
            except DocumentType.DoesNotExist:
                item["name"] = f"Type #{item['id']}"

        for item in suggestions.get("storage_path", []):
            try:
                item["name"] = StoragePath.objects.get(pk=item["id"]).name
            except StoragePath.DoesNotExist:
                item["name"] = f"Path #{item['id']}"


class ClassifierStatusView(APIView):
    """GET /api/v1/classifier/status/

    Returns the current status of the trained classifier.
    """

    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        classifier = get_classifier()

        if classifier is None:
            data = {
                "available": False,
                "tags_trained": False,
                "correspondent_trained": False,
                "document_type_trained": False,
                "storage_path_trained": False,
            }
        else:
            data = {
                "available": True,
                "format_version": classifier.format_version,
                "tags_trained": classifier.tags_classifier is not None,
                "correspondent_trained": classifier.correspondent_classifier is not None,
                "document_type_trained": classifier.document_type_classifier is not None,
                "storage_path_trained": classifier.storage_path_classifier is not None,
                "tags_data_hash": classifier.tags_data_hash,
                "correspondent_data_hash": classifier.correspondent_data_hash,
                "document_type_data_hash": classifier.document_type_data_hash,
                "storage_path_data_hash": classifier.storage_path_data_hash,
            }

        serializer = ClassifierStatusSerializer(data)
        return Response(serializer.data)


class ClassifierTrainView(APIView):
    """POST /api/v1/classifier/train/

    Trigger classifier training manually.
    """

    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        from .tasks import train_classifier
        train_classifier.delay()
        return Response(
            {"status": "training_queued"},
            status=status.HTTP_202_ACCEPTED,
        )

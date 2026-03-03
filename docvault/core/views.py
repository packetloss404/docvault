"""Core API views for user preferences and bulk operations."""

import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .preferences import UserPreferences

logger = logging.getLogger(__name__)


class UserPreferencesView(APIView):
    """Get or update the current user's preferences (theme, language, dashboard)."""

    def get(self, request):
        prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
        return Response({
            "theme": prefs.theme,
            "language": prefs.language,
            "dashboard_layout": prefs.dashboard_layout,
        })

    def patch(self, request):
        prefs, _ = UserPreferences.objects.get_or_create(user=request.user)

        if "theme" in request.data:
            if request.data["theme"] in ("light", "dark", "system"):
                prefs.theme = request.data["theme"]

        if "language" in request.data:
            prefs.language = request.data["language"]

        if "dashboard_layout" in request.data:
            prefs.dashboard_layout = request.data["dashboard_layout"]

        prefs.save()
        return Response({
            "theme": prefs.theme,
            "language": prefs.language,
            "dashboard_layout": prefs.dashboard_layout,
        })


class BulkOperationView(APIView):
    """Perform bulk operations on documents."""

    def post(self, request):
        from documents.models import Document

        action = request.data.get("action")
        document_ids = request.data.get("document_ids", [])

        if not action or not document_ids:
            return Response(
                {"error": "Both 'action' and 'document_ids' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        documents = Document.objects.filter(pk__in=document_ids)
        count = documents.count()

        if count == 0:
            return Response(
                {"error": "No documents found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if action == "add_tags":
            tag_ids = request.data.get("tag_ids", [])
            if not tag_ids:
                return Response(
                    {"error": "'tag_ids' required for add_tags action."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            from organization.models import Tag
            tags = Tag.objects.filter(pk__in=tag_ids)
            for doc in documents:
                doc.tags.add(*tags)
            return Response({"action": "add_tags", "affected": count})

        elif action == "remove_tags":
            tag_ids = request.data.get("tag_ids", [])
            from organization.models import Tag
            tags = Tag.objects.filter(pk__in=tag_ids)
            for doc in documents:
                doc.tags.remove(*tags)
            return Response({"action": "remove_tags", "affected": count})

        elif action == "set_correspondent":
            correspondent_id = request.data.get("correspondent_id")
            documents.update(correspondent_id=correspondent_id)
            return Response({"action": "set_correspondent", "affected": count})

        elif action == "set_document_type":
            document_type_id = request.data.get("document_type_id")
            documents.update(document_type_id=document_type_id)
            return Response({"action": "set_document_type", "affected": count})

        elif action == "delete":
            for doc in documents:
                doc.soft_delete()
            return Response({"action": "delete", "affected": count})

        else:
            return Response(
                {"error": f"Unknown action: {action}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

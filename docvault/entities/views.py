"""Views for the entities app."""

from django.db.models import Count, F
from rest_framework import permissions, status, viewsets
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.serializers import DocumentListSerializer

from .models import Entity, EntityType
from .serializers import (
    EntityAggregateSerializer,
    EntitySerializer,
    EntityTypeSerializer,
)


class EntityTypeViewSet(viewsets.ModelViewSet):
    """
    CRUD for entity types.

    GET    /api/v1/entity-types/          - list
    POST   /api/v1/entity-types/          - create (admin)
    GET    /api/v1/entity-types/{id}/     - detail
    PATCH  /api/v1/entity-types/{id}/     - update (admin)
    DELETE /api/v1/entity-types/{id}/     - delete (admin)
    """

    queryset = EntityType.objects.all()
    serializer_class = EntityTypeSerializer
    search_fields = ["name", "label"]
    ordering_fields = ["name", "label"]
    ordering = ["name"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]


class EntityListView(ListAPIView):
    """
    List entities with optional filtering and aggregation.

    GET /api/v1/entities/?document_id=1&entity_type=PERSON&value=John
    GET /api/v1/entities/?aggregate=true   (grouped by value with doc count)
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.query_params.get("aggregate") == "true":
            return EntityAggregateSerializer
        return EntitySerializer

    def get_queryset(self):
        qs = Entity.objects.select_related("entity_type")

        document_id = self.request.query_params.get("document_id")
        if document_id:
            qs = qs.filter(document_id=document_id)

        entity_type = self.request.query_params.get("entity_type")
        if entity_type:
            qs = qs.filter(entity_type__name=entity_type)

        value = self.request.query_params.get("value")
        if value:
            qs = qs.filter(value__icontains=value)

        return qs

    def list(self, request, *args, **kwargs):
        if request.query_params.get("aggregate") == "true":
            qs = self.get_queryset()
            aggregated = (
                qs.values(
                    "value",
                    entity_type_name=F("entity_type__name"),
                    entity_type_color=F("entity_type__color"),
                )
                .annotate(document_count=Count("document", distinct=True))
                .order_by("-document_count")
            )
            serializer = EntityAggregateSerializer(aggregated, many=True)
            return Response(serializer.data)
        return super().list(request, *args, **kwargs)


class DocumentEntityListView(ListAPIView):
    """
    List entities for a specific document.

    GET /api/v1/documents/{document_id}/entities/
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EntitySerializer

    def get_queryset(self):
        return (
            Entity.objects
            .filter(document_id=self.kwargs["document_id"])
            .select_related("entity_type")
        )


class EntityDocumentsView(APIView):
    """
    List documents that contain a specific entity.

    GET /api/v1/entities/{entity_type}/{value}/documents/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, entity_type, value):
        from documents.models import Document

        document_ids = (
            Entity.objects
            .filter(entity_type__name=entity_type, value=value)
            .values_list("document_id", flat=True)
            .distinct()
        )
        documents = Document.objects.filter(pk__in=document_ids)

        # Permission: non-superusers only see their own documents.
        if not request.user.is_superuser:
            documents = documents.filter(owner=request.user)

        serializer = DocumentListSerializer(documents, many=True)
        return Response(serializer.data)

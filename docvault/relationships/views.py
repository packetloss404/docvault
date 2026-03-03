"""API views for the relationships module."""

import logging
from collections import deque

from django.db.models import Q
from django.http import Http404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.models import Document

from .models import DocumentRelationship, RelationshipType
from .serializers import (
    DocumentRelationshipCreateSerializer,
    DocumentRelationshipSerializer,
    RelationshipGraphSerializer,
    RelationshipTypeSerializer,
)

logger = logging.getLogger(__name__)


# --- Relationship Types ---


class RelationshipTypeListCreateView(APIView):
    """GET/POST /api/v1/relationship-types/"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        types = RelationshipType.objects.all()
        serializer = RelationshipTypeSerializer(types, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not request.user.is_superuser:
            return Response(
                {"error": "Only administrators can create relationship types."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RelationshipTypeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rel_type = RelationshipType.objects.create(
            **serializer.validated_data,
            is_builtin=False,
            created_by=request.user,
        )

        return Response(
            RelationshipTypeSerializer(rel_type).data,
            status=status.HTTP_201_CREATED,
        )


class RelationshipTypeDetailView(APIView):
    """GET/PATCH/DELETE /api/v1/relationship-types/<pk>/"""

    permission_classes = [permissions.IsAuthenticated]

    def _get_object(self, pk):
        try:
            return RelationshipType.objects.get(pk=pk)
        except RelationshipType.DoesNotExist:
            raise Http404("Relationship type not found.")

    def get(self, request, pk):
        rel_type = self._get_object(pk)
        return Response(RelationshipTypeSerializer(rel_type).data)

    def patch(self, request, pk):
        if not request.user.is_superuser:
            return Response(
                {"error": "Only administrators can modify relationship types."},
                status=status.HTTP_403_FORBIDDEN,
            )

        rel_type = self._get_object(pk)

        serializer = RelationshipTypeSerializer(
            rel_type, data=request.data, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)

        return Response(serializer.data)

    def delete(self, request, pk):
        if not request.user.is_superuser:
            return Response(
                {"error": "Only administrators can delete relationship types."},
                status=status.HTTP_403_FORBIDDEN,
            )

        rel_type = self._get_object(pk)

        if rel_type.is_builtin:
            return Response(
                {"error": "Built-in relationship types cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rel_type.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Document Relationships ---


class DocumentRelationshipListCreateView(APIView):
    """GET/POST /api/v1/documents/<document_id>/relationships/"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, document_id):
        try:
            Document.objects.get(pk=document_id)
        except Document.DoesNotExist:
            raise Http404("Document not found.")

        relationships = (
            DocumentRelationship.objects.filter(
                Q(source_document_id=document_id)
                | Q(target_document_id=document_id)
            )
            .select_related(
                "source_document",
                "target_document",
                "relationship_type",
            )
        )

        serializer = DocumentRelationshipSerializer(relationships, many=True)
        return Response(serializer.data)

    def post(self, request, document_id):
        try:
            source = Document.objects.get(pk=document_id)
        except Document.DoesNotExist:
            raise Http404("Document not found.")

        serializer = DocumentRelationshipCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_id = serializer.validated_data["target_document"]
        try:
            target = Document.objects.get(pk=target_id)
        except Document.DoesNotExist:
            return Response(
                {"error": "Target document not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if source.pk == target.pk:
            return Response(
                {"error": "A document cannot have a relationship with itself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rel_type_id = serializer.validated_data["relationship_type"]
        try:
            rel_type = RelationshipType.objects.get(pk=rel_type_id)
        except RelationshipType.DoesNotExist:
            return Response(
                {"error": "Relationship type not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        relationship, created = DocumentRelationship.objects.get_or_create(
            source_document=source,
            target_document=target,
            relationship_type=rel_type,
            defaults={
                "notes": serializer.validated_data["notes"],
                "created_by": request.user,
            },
        )

        if not created:
            return Response(
                {"error": "This relationship already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        output = DocumentRelationshipSerializer(relationship).data
        return Response(output, status=status.HTTP_201_CREATED)


class DocumentRelationshipDeleteView(APIView):
    """DELETE /api/v1/documents/<document_id>/relationships/<pk>/"""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, document_id, pk):
        try:
            relationship = DocumentRelationship.objects.get(
                pk=pk,
                source_document_id=document_id,
            )
        except DocumentRelationship.DoesNotExist:
            # Also allow deletion from the target side
            try:
                relationship = DocumentRelationship.objects.get(
                    pk=pk,
                    target_document_id=document_id,
                )
            except DocumentRelationship.DoesNotExist:
                raise Http404("Relationship not found.")

        relationship.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Relationship Graph ---


class DocumentRelationshipGraphView(APIView):
    """GET /api/v1/documents/<document_id>/relationship-graph/?depth=2

    Returns a graph of related documents using BFS traversal from the
    given document up to ``depth`` hops (default 2, max 3).
    """

    permission_classes = [permissions.IsAuthenticated]

    MAX_DEPTH = 3
    DEFAULT_DEPTH = 2

    def get(self, request, document_id):
        try:
            root = Document.objects.select_related("document_type").get(
                pk=document_id,
            )
        except Document.DoesNotExist:
            raise Http404("Document not found.")

        depth = self._parse_depth(request)

        nodes, edges = self._bfs(root, depth)

        serializer = RelationshipGraphSerializer(
            {"nodes": nodes, "edges": edges},
        )
        return Response(serializer.data)

    def _parse_depth(self, request):
        try:
            depth = int(request.query_params.get("depth", self.DEFAULT_DEPTH))
        except (TypeError, ValueError):
            depth = self.DEFAULT_DEPTH
        return min(max(depth, 1), self.MAX_DEPTH)

    def _bfs(self, root, max_depth):
        """Breadth-first traversal collecting nodes and edges."""
        visited_ids = set()
        node_map = {}
        edges = []

        queue = deque()
        queue.append((root.pk, 0))
        visited_ids.add(root.pk)
        node_map[root.pk] = self._make_node(root)

        while queue:
            current_id, current_depth = queue.popleft()

            if current_depth >= max_depth:
                continue

            relationships = (
                DocumentRelationship.objects.filter(
                    Q(source_document_id=current_id)
                    | Q(target_document_id=current_id)
                )
                .select_related(
                    "source_document",
                    "source_document__document_type",
                    "target_document",
                    "target_document__document_type",
                    "relationship_type",
                )
            )

            for rel in relationships:
                edges.append({
                    "source": rel.source_document_id,
                    "target": rel.target_document_id,
                    "type": rel.relationship_type.slug,
                    "label": rel.relationship_type.label,
                })

                # Determine the neighbour (the other document)
                if rel.source_document_id == current_id:
                    neighbour = rel.target_document
                else:
                    neighbour = rel.source_document

                if neighbour.pk not in visited_ids:
                    visited_ids.add(neighbour.pk)
                    node_map[neighbour.pk] = self._make_node(neighbour)
                    queue.append((neighbour.pk, current_depth + 1))

        # Deduplicate edges (same pair + type can appear from both sides)
        unique_edges = list(
            {
                (e["source"], e["target"], e["type"]): e
                for e in edges
            }.values()
        )

        return list(node_map.values()), unique_edges

    @staticmethod
    def _make_node(document):
        return {
            "id": document.pk,
            "title": document.title,
            "document_type": (
                document.document_type.name
                if document.document_type
                else None
            ),
        }

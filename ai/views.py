"""API views for AI features."""

from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    DocumentChatSerializer,
    GlobalChatSerializer,
    SemanticSearchSerializer,
)


class SemanticSearchView(APIView):
    """GET /api/v1/ai/search/semantic/?query=...&k=10 — Semantic vector search."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = SemanticSearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        user_id = None
        if not request.user.is_superuser:
            user_id = request.user.id

        from .search import semantic_search

        results = semantic_search(
            query=serializer.validated_data["query"],
            k=serializer.validated_data["k"],
            user_id=user_id,
        )

        return Response({"results": results, "count": len(results)})


class HybridSearchView(APIView):
    """GET /api/v1/ai/search/hybrid/?query=...&k=10 — Combined keyword + semantic search."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = SemanticSearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        user_id = None
        if not request.user.is_superuser:
            user_id = request.user.id

        from .search import hybrid_search

        results = hybrid_search(
            query=serializer.validated_data["query"],
            k=serializer.validated_data["k"],
            user_id=user_id,
        )

        return Response({"results": results, "count": len(results)})


class SimilarDocumentsAIView(APIView):
    """GET /api/v1/ai/similar/{id}/ — Find similar docs via vector similarity."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        k = int(request.query_params.get("k", 10))
        k = min(k, 50)

        user_id = None
        if not request.user.is_superuser:
            user_id = request.user.id

        from .search import find_similar_documents

        results = find_similar_documents(
            document_id=pk,
            k=k,
            user_id=user_id,
        )

        return Response({"results": results, "count": len(results)})


class DocumentChatView(APIView):
    """POST /api/v1/ai/documents/{id}/chat/ — Chat about a specific document."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        serializer = DocumentChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from .chat import chat_with_document

        result = chat_with_document(
            document_id=pk,
            question=serializer.validated_data["question"],
            history=serializer.validated_data.get("history", []),
        )

        return Response(result)


class GlobalChatView(APIView):
    """POST /api/v1/ai/chat/ — Chat across all documents (RAG)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = GlobalChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = None
        if not request.user.is_superuser:
            user_id = request.user.id

        from .chat import chat_across_documents

        result = chat_across_documents(
            question=serializer.validated_data["question"],
            user_id=user_id,
            history=serializer.validated_data.get("history", []),
        )

        return Response(result)


class SummarizeView(APIView):
    """GET /api/v1/ai/documents/{id}/summarize/ — Summarize a document."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        from .features import summarize_document

        result = summarize_document(document_id=pk)
        if result.get("error"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class EntityExtractView(APIView):
    """GET /api/v1/ai/documents/{id}/entities/ — Extract entities from a document."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        from .features import extract_entities

        result = extract_entities(document_id=pk)
        if result.get("error"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class SmartTitleView(APIView):
    """GET /api/v1/ai/documents/{id}/suggest-title/ — Suggest a title."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        from .features import suggest_title

        result = suggest_title(document_id=pk)
        if result.get("error"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class AIConfigView(APIView):
    """GET /api/v1/ai/config/ — Get current AI configuration (admin only)."""

    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from .vector_store import get_vector_store

        store = get_vector_store()

        return Response({
            "llm_enabled": getattr(settings, "LLM_ENABLED", False),
            "llm_provider": getattr(settings, "LLM_PROVIDER", "disabled"),
            "llm_model": getattr(settings, "LLM_MODEL", ""),
            "embedding_model": getattr(settings, "EMBEDDING_MODEL", ""),
            "vector_store_count": store.count,
        })


class AIStatusView(APIView):
    """GET /api/v1/ai/status/ — Get AI system status."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .client import get_llm_client
        from .vector_store import get_vector_store

        client = get_llm_client()
        store = get_vector_store()

        return Response({
            "llm_enabled": getattr(settings, "LLM_ENABLED", False),
            "llm_provider": getattr(settings, "LLM_PROVIDER", "disabled"),
            "llm_model": getattr(settings, "LLM_MODEL", ""),
            "embedding_model": getattr(settings, "EMBEDDING_MODEL", ""),
            "vector_store_count": store.count,
            "llm_available": client is not None,
        })


class RebuildVectorIndexView(APIView):
    """POST /api/v1/ai/rebuild-index/ — Trigger vector index rebuild (admin only)."""

    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        from .tasks import rebuild_vector_index

        rebuild_vector_index.delay()
        return Response(
            {"status": "started", "message": "Vector index rebuild started."},
            status=status.HTTP_202_ACCEPTED,
        )

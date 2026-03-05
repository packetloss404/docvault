"""Search API views."""

from datetime import timedelta

from django.db.models import Avg, Count, F, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.serializers import DocumentListSerializer

from .models import SavedView, SearchCuration, SearchQuery, SearchSynonym
from .query import execute_autocomplete, execute_more_like_this, execute_search
from .saved_view_executor import execute_saved_view
from .serializers import (
    SavedViewListSerializer,
    SavedViewSerializer,
    SearchAnalyticsSerializer,
    SearchCurationSerializer,
    SearchSynonymSerializer,
)


class SearchView(APIView):
    """
    Full-text search with faceted filtering and highlighting.

    GET /api/v1/search/?query=invoice&page=1&page_size=25
    Supports field-specific queries: tag:finance, correspondent:acme
    Supports date ranges: created:[2025-01-01 TO 2025-12-31]
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("query", "")
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 25))
        page_size = min(page_size, 100)  # Cap at 100

        # Optional filters
        filters = {}
        if request.query_params.get("document_type_id"):
            filters["document_type_id"] = int(
                request.query_params["document_type_id"],
            )
        if request.query_params.get("correspondent_id"):
            filters["correspondent_id"] = int(
                request.query_params["correspondent_id"],
            )
        if request.query_params.get("tag_ids"):
            filters["tag_ids"] = [
                int(x) for x in request.query_params["tag_ids"].split(",")
            ]
        if request.query_params.get("cabinet_id"):
            filters["cabinet_id"] = int(request.query_params["cabinet_id"])
        if request.query_params.get("created_after"):
            filters["created_after"] = request.query_params["created_after"]
        if request.query_params.get("created_before"):
            filters["created_before"] = request.query_params["created_before"]
        if request.query_params.get("language"):
            filters["language"] = request.query_params["language"]
        if request.query_params.get("mime_type"):
            filters["mime_type"] = request.query_params["mime_type"]

        # Permission: non-superusers only see their own docs
        user_id = None
        if not request.user.is_superuser:
            user_id = request.user.id

        results = execute_search(
            query_text=query,
            user_id=user_id,
            filters=filters,
            page=page,
            page_size=page_size,
        )

        return Response(results)


class SearchAutocompleteView(APIView):
    """
    Typeahead suggestions for the search bar.

    GET /api/v1/search/autocomplete/?query=inv
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("query", "")
        limit = int(request.query_params.get("limit", 10))
        limit = min(limit, 20)

        if len(query) < 2:
            return Response([])

        user_id = None
        if not request.user.is_superuser:
            user_id = request.user.id

        suggestions = execute_autocomplete(
            query_text=query,
            user_id=user_id,
            limit=limit,
        )

        return Response(suggestions)


class SimilarDocumentsView(APIView):
    """
    Find documents similar to a given document (More Like This).

    GET /api/v1/search/similar/{id}/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        limit = int(request.query_params.get("limit", 10))
        limit = min(limit, 20)

        user_id = None
        if not request.user.is_superuser:
            user_id = request.user.id

        results = execute_more_like_this(
            document_id=pk,
            user_id=user_id,
            limit=limit,
        )

        return Response(results)


class SavedViewViewSet(viewsets.ModelViewSet):
    """
    CRUD for saved views with execute action.

    GET /api/v1/saved-views/ - List saved views
    POST /api/v1/saved-views/ - Create saved view with filter rules
    GET /api/v1/saved-views/{id}/ - Get saved view
    PATCH /api/v1/saved-views/{id}/ - Update saved view
    DELETE /api/v1/saved-views/{id}/ - Delete saved view
    GET /api/v1/saved-views/{id}/execute/ - Execute and return results
    """

    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        return SavedView.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return SavedViewListSerializer
        return SavedViewSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["get"])
    def execute(self, request, pk=None):
        """Execute the saved view and return paginated document results."""
        saved_view = self.get_object()
        qs = execute_saved_view(saved_view, user=request.user)

        # Apply pagination
        page_size = saved_view.page_size or 25
        page_num = int(request.query_params.get("page", 1))

        from core.pagination import StandardPagination

        paginator = StandardPagination()
        paginator.page_size = page_size
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = DocumentListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = DocumentListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        """Get saved views configured for dashboard display."""
        views = self.get_queryset().filter(show_on_dashboard=True)
        serializer = SavedViewListSerializer(views, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def sidebar(self, request):
        """Get saved views configured for sidebar display."""
        views = self.get_queryset().filter(show_in_sidebar=True)
        serializer = SavedViewListSerializer(views, many=True)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Search analytics views (Sprint 19)
# ---------------------------------------------------------------------------


class SearchClickView(APIView):
    """
    Record a click on a search result for relevance analytics.

    POST /api/v1/search/click/
    Body: {"query_text": "...", "document_id": 123, "click_position": 1}
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        query_text = request.data.get("query_text", "")
        document_id = request.data.get("document_id")
        click_position = request.data.get("click_position")

        if not query_text:
            return Response(
                {"detail": "query_text is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find the most recent matching search query for this user, or create one.
        sq = (
            SearchQuery.objects
            .filter(user=request.user, query_text=query_text)
            .order_by("-timestamp")
            .first()
        )
        if sq:
            sq.clicked_document_id = document_id
            sq.click_position = click_position
            sq.save(update_fields=["clicked_document_id", "click_position"])
        else:
            SearchQuery.objects.create(
                user=request.user,
                query_text=query_text,
                clicked_document_id=document_id,
                click_position=click_position,
            )

        return Response({"detail": "Click recorded."}, status=status.HTTP_200_OK)


class SearchAnalyticsView(APIView):
    """
    Aggregated search analytics dashboard (admin only).

    GET /api/v1/search/analytics/?days=30
    """

    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get("days", 30))
        days = min(days, 365)
        since = timezone.now() - timedelta(days=days)

        qs = SearchQuery.objects.filter(timestamp__gte=since)

        # Top queries by frequency.
        top_queries = list(
            qs.values("query_text")
            .annotate(count=Count("id"))
            .order_by("-count")[:20]
        )

        # Queries that returned zero results.
        zero_result_queries = list(
            qs.filter(results_count=0)
            .values("query_text")
            .annotate(count=Count("id"))
            .order_by("-count")[:20]
        )

        # Click-through rate.
        total = qs.count()
        clicked = qs.filter(clicked_document__isnull=False).count()
        average_ctr = (clicked / total * 100) if total else 0.0

        # Daily query volume.
        query_volume = list(
            qs.annotate(date=TruncDate("timestamp"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )
        # Serialize dates to ISO strings.
        for entry in query_volume:
            entry["date"] = entry["date"].isoformat()

        data = {
            "top_queries": top_queries,
            "zero_result_queries": zero_result_queries,
            "average_ctr": round(average_ctr, 2),
            "query_volume": query_volume,
            "total_queries": total,
            "total_clicks": clicked,
        }

        serializer = SearchAnalyticsSerializer(data)
        return Response(serializer.data)


class SearchSynonymViewSet(viewsets.ModelViewSet):
    """
    CRUD for search synonym groups (admin only).

    GET    /api/v1/search/synonyms/
    POST   /api/v1/search/synonyms/
    GET    /api/v1/search/synonyms/{id}/
    PATCH  /api/v1/search/synonyms/{id}/
    DELETE /api/v1/search/synonyms/{id}/
    """

    queryset = SearchSynonym.objects.all()
    serializer_class = SearchSynonymSerializer
    permission_classes = [permissions.IsAdminUser]
    ordering = ["created_at"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class SearchCurationViewSet(viewsets.ModelViewSet):
    """
    CRUD for curated search results (admin only).

    GET    /api/v1/search/curations/
    POST   /api/v1/search/curations/
    GET    /api/v1/search/curations/{id}/
    PATCH  /api/v1/search/curations/{id}/
    DELETE /api/v1/search/curations/{id}/
    """

    queryset = SearchCuration.objects.all()
    serializer_class = SearchCurationSerializer
    permission_classes = [permissions.IsAdminUser]
    ordering = ["query_text"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

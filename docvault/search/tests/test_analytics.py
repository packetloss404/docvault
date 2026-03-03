"""Tests for search analytics: SearchQuery, SearchSynonym, SearchCuration, and related views."""

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from documents.models import Document
from search.models import SearchCuration, SearchQuery, SearchSynonym


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="analyticadmin", password="adminpass", email="admin@test.com",
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(username="analyticuser", password="testpass")


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


@pytest.fixture
def regular_client(regular_user):
    c = APIClient()
    c.force_authenticate(user=regular_user)
    return c


@pytest.fixture
def anon_client():
    return APIClient()


@pytest.fixture
def document(admin_user):
    return Document.objects.create(
        title="Analytics Test Doc",
        content="Test document for search analytics.",
        owner=admin_user,
    )


@pytest.fixture
def document2(admin_user):
    return Document.objects.create(
        title="Second Analytics Doc",
        content="Another doc for testing.",
        owner=admin_user,
    )


@pytest.fixture
def search_query(admin_user):
    return SearchQuery.objects.create(
        query_text="invoice",
        user=admin_user,
        results_count=10,
        response_time_ms=150,
    )


@pytest.fixture
def search_synonym(admin_user):
    return SearchSynonym.objects.create(
        terms=["invoice", "bill", "receipt"],
        enabled=True,
        created_by=admin_user,
    )


@pytest.fixture
def search_curation(admin_user):
    return SearchCuration.objects.create(
        query_text="important docs",
        boost_fields={"title": 3.0},
        enabled=True,
        created_by=admin_user,
    )


# ---- Model tests ----


@pytest.mark.django_db
class TestSearchQueryModel:
    def test_create_search_query(self, search_query, admin_user):
        assert search_query.pk is not None
        assert search_query.query_text == "invoice"
        assert search_query.user == admin_user
        assert search_query.results_count == 10
        assert search_query.response_time_ms == 150
        assert search_query.timestamp is not None

    def test_str_representation(self, search_query):
        s = str(search_query)
        assert "invoice" in s

    def test_ordering_by_timestamp_desc(self, admin_user):
        sq1 = SearchQuery.objects.create(query_text="first", user=admin_user)
        sq2 = SearchQuery.objects.create(query_text="second", user=admin_user)
        queries = list(SearchQuery.objects.values_list("query_text", flat=True)[:2])
        # Most recent first
        assert queries[0] == "second"
        assert queries[1] == "first"

    def test_default_values(self, admin_user):
        sq = SearchQuery.objects.create(query_text="test", user=admin_user)
        assert sq.results_count == 0
        assert sq.clicked_document is None
        assert sq.click_position is None
        assert sq.response_time_ms == 0

    def test_clicked_document_set_null(self, admin_user, document):
        sq = SearchQuery.objects.create(
            query_text="test", user=admin_user, clicked_document=document,
        )
        document.hard_delete()
        sq.refresh_from_db()
        assert sq.clicked_document is None


@pytest.mark.django_db
class TestSearchSynonymModel:
    def test_create_synonym(self, search_synonym):
        assert search_synonym.pk is not None
        assert search_synonym.terms == ["invoice", "bill", "receipt"]
        assert search_synonym.enabled is True

    def test_str_representation(self, search_synonym):
        s = str(search_synonym)
        assert "invoice" in s
        assert "bill" in s

    def test_empty_terms_str(self, admin_user):
        syn = SearchSynonym.objects.create(terms=[], created_by=admin_user)
        assert str(syn) == "(empty)"

    def test_default_enabled(self, admin_user):
        syn = SearchSynonym.objects.create(terms=["a", "b"], created_by=admin_user)
        assert syn.enabled is True


@pytest.mark.django_db
class TestSearchCurationModel:
    def test_create_curation(self, search_curation):
        assert search_curation.pk is not None
        assert search_curation.query_text == "important docs"
        assert search_curation.boost_fields == {"title": 3.0}

    def test_str_representation(self, search_curation):
        assert "important docs" in str(search_curation)

    def test_unique_query_text(self, admin_user):
        SearchCuration.objects.create(query_text="unique", created_by=admin_user)
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            SearchCuration.objects.create(query_text="unique", created_by=admin_user)

    def test_m2m_pinned_documents(self, search_curation, document, document2):
        search_curation.pinned_documents.add(document, document2)
        assert search_curation.pinned_documents.count() == 2

    def test_m2m_hidden_documents(self, search_curation, document):
        search_curation.hidden_documents.add(document)
        assert search_curation.hidden_documents.count() == 1


# ---- SearchClickView ----


@pytest.mark.django_db
class TestSearchClickView:
    def test_record_click_creates_query(self, regular_client, regular_user, document):
        data = {
            "query_text": "test query",
            "document_id": document.pk,
            "click_position": 1,
        }
        response = regular_client.post("/api/v1/search/click/", data, format="json")
        assert response.status_code == 200
        assert response.data["detail"] == "Click recorded."

        sq = SearchQuery.objects.filter(user=regular_user, query_text="test query").first()
        assert sq is not None
        assert sq.clicked_document_id == document.pk
        assert sq.click_position == 1

    def test_record_click_updates_existing_query(self, regular_client, regular_user, document):
        SearchQuery.objects.create(
            query_text="test query", user=regular_user, results_count=5,
        )
        data = {
            "query_text": "test query",
            "document_id": document.pk,
            "click_position": 3,
        }
        response = regular_client.post("/api/v1/search/click/", data, format="json")
        assert response.status_code == 200

        sq = SearchQuery.objects.filter(user=regular_user, query_text="test query").first()
        assert sq.clicked_document_id == document.pk
        assert sq.click_position == 3

    def test_record_click_missing_query_text(self, regular_client):
        data = {"document_id": 1, "click_position": 1}
        response = regular_client.post("/api/v1/search/click/", data, format="json")
        assert response.status_code == 400

    def test_record_click_unauthenticated(self, anon_client):
        data = {"query_text": "test", "document_id": 1}
        response = anon_client.post("/api/v1/search/click/", data, format="json")
        assert response.status_code in (401, 403)


# ---- SearchAnalyticsView ----


@pytest.mark.django_db
class TestSearchAnalyticsView:
    def test_analytics_admin_access(self, admin_client, admin_user):
        SearchQuery.objects.create(query_text="invoice", user=admin_user, results_count=10)
        SearchQuery.objects.create(query_text="invoice", user=admin_user, results_count=5)
        SearchQuery.objects.create(query_text="receipt", user=admin_user, results_count=0)

        response = admin_client.get("/api/v1/search/analytics/")
        assert response.status_code == 200
        data = response.data
        assert "top_queries" in data
        assert "zero_result_queries" in data
        assert "average_ctr" in data
        assert "query_volume" in data
        assert "total_queries" in data
        assert "total_clicks" in data
        assert data["total_queries"] == 3

    def test_analytics_non_admin_forbidden(self, regular_client):
        response = regular_client.get("/api/v1/search/analytics/")
        assert response.status_code == 403

    def test_analytics_unauthenticated_forbidden(self, anon_client):
        response = anon_client.get("/api/v1/search/analytics/")
        assert response.status_code in (401, 403)

    def test_analytics_days_filter(self, admin_client, admin_user):
        # Create a query within the last 7 days
        SearchQuery.objects.create(query_text="recent", user=admin_user, results_count=5)
        response = admin_client.get("/api/v1/search/analytics/?days=7")
        assert response.status_code == 200
        assert response.data["total_queries"] >= 1

    def test_analytics_zero_result_queries(self, admin_client, admin_user):
        SearchQuery.objects.create(query_text="no results", user=admin_user, results_count=0)
        SearchQuery.objects.create(query_text="has results", user=admin_user, results_count=10)

        response = admin_client.get("/api/v1/search/analytics/")
        zero_queries = response.data["zero_result_queries"]
        zero_texts = [q["query_text"] for q in zero_queries]
        assert "no results" in zero_texts

    def test_analytics_click_through_rate(self, admin_client, admin_user, document):
        # 2 queries, 1 with click
        SearchQuery.objects.create(query_text="q1", user=admin_user, results_count=5)
        SearchQuery.objects.create(
            query_text="q2", user=admin_user, results_count=5,
            clicked_document=document,
        )

        response = admin_client.get("/api/v1/search/analytics/")
        assert response.data["total_queries"] == 2
        assert response.data["total_clicks"] == 1
        assert response.data["average_ctr"] == 50.0


# ---- SearchSynonymViewSet ----


@pytest.mark.django_db
class TestSearchSynonymViewSet:
    def test_list_synonyms(self, admin_client, search_synonym):
        response = admin_client.get("/api/v1/search/synonyms/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_create_synonym(self, admin_client):
        data = {"terms": ["car", "automobile", "vehicle"], "enabled": True}
        response = admin_client.post("/api/v1/search/synonyms/", data, format="json")
        assert response.status_code == 201
        synonym = SearchSynonym.objects.get(pk=response.data["id"])
        assert "car" in synonym.terms
        assert "automobile" in synonym.terms

    def test_retrieve_synonym(self, admin_client, search_synonym):
        response = admin_client.get(f"/api/v1/search/synonyms/{search_synonym.pk}/")
        assert response.status_code == 200
        assert response.data["terms"] == ["invoice", "bill", "receipt"]

    def test_update_synonym(self, admin_client, search_synonym):
        data = {"terms": ["invoice", "bill"]}
        response = admin_client.patch(
            f"/api/v1/search/synonyms/{search_synonym.pk}/", data, format="json",
        )
        assert response.status_code == 200
        search_synonym.refresh_from_db()
        assert search_synonym.terms == ["invoice", "bill"]

    def test_delete_synonym(self, admin_client, search_synonym):
        response = admin_client.delete(f"/api/v1/search/synonyms/{search_synonym.pk}/")
        assert response.status_code == 204
        assert not SearchSynonym.objects.filter(pk=search_synonym.pk).exists()

    def test_non_admin_forbidden(self, regular_client):
        response = regular_client.get("/api/v1/search/synonyms/")
        assert response.status_code == 403

    def test_unauthenticated_forbidden(self, anon_client):
        response = anon_client.get("/api/v1/search/synonyms/")
        assert response.status_code in (401, 403)


# ---- SearchCurationViewSet ----


@pytest.mark.django_db
class TestSearchCurationViewSet:
    def test_list_curations(self, admin_client, search_curation):
        response = admin_client.get("/api/v1/search/curations/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_create_curation(self, admin_client, document):
        data = {
            "query_text": "new curation",
            "pinned_documents": [document.pk],
            "hidden_documents": [],
            "boost_fields": {"title": 2.0},
            "enabled": True,
        }
        response = admin_client.post("/api/v1/search/curations/", data, format="json")
        assert response.status_code == 201
        assert SearchCuration.objects.filter(query_text="new curation").exists()
        curation = SearchCuration.objects.get(query_text="new curation")
        assert curation.pinned_documents.count() == 1

    def test_retrieve_curation(self, admin_client, search_curation):
        response = admin_client.get(f"/api/v1/search/curations/{search_curation.pk}/")
        assert response.status_code == 200
        assert response.data["query_text"] == "important docs"

    def test_update_curation(self, admin_client, search_curation):
        data = {"boost_fields": {"title": 5.0, "content": 2.0}}
        response = admin_client.patch(
            f"/api/v1/search/curations/{search_curation.pk}/", data, format="json",
        )
        assert response.status_code == 200
        search_curation.refresh_from_db()
        assert search_curation.boost_fields == {"title": 5.0, "content": 2.0}

    def test_delete_curation(self, admin_client, search_curation):
        response = admin_client.delete(f"/api/v1/search/curations/{search_curation.pk}/")
        assert response.status_code == 204
        assert not SearchCuration.objects.filter(pk=search_curation.pk).exists()

    def test_non_admin_forbidden(self, regular_client):
        response = regular_client.get("/api/v1/search/curations/")
        assert response.status_code == 403

    def test_unauthenticated_forbidden(self, anon_client):
        response = anon_client.get("/api/v1/search/curations/")
        assert response.status_code in (401, 403)

    def test_create_curation_with_m2m(self, admin_client, document, document2):
        data = {
            "query_text": "m2m test",
            "pinned_documents": [document.pk],
            "hidden_documents": [document2.pk],
            "boost_fields": {},
            "enabled": True,
        }
        response = admin_client.post("/api/v1/search/curations/", data, format="json")
        assert response.status_code == 201
        curation = SearchCuration.objects.get(query_text="m2m test")
        assert curation.pinned_documents.count() == 1
        assert curation.hidden_documents.count() == 1

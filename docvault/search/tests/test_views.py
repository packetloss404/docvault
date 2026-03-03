"""Tests for search API views."""

from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from documents.models import Document
from organization.models import Correspondent, Tag

from search.models import (
    RULE_HAS_TAGS,
    RULE_TAG_IS,
    RULE_TITLE_CONTAINS,
    SavedView,
    SavedViewFilterRule,
)


class SearchViewTest(TestCase):
    """Tests for the search API endpoint (ES mocked)."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="searcher", password="pass!")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    @patch("search.views.execute_search")
    def test_search_endpoint(self, mock_search):
        mock_search.return_value = {
            "count": 1,
            "page": 1,
            "page_size": 25,
            "results": [
                {"id": 1, "title": "Invoice", "score": 5.2},
            ],
            "facets": {},
        }
        resp = self.client.get("/api/v1/search/", {"query": "invoice"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(len(resp.data["results"]), 1)
        mock_search.assert_called_once()

    @patch("search.views.execute_search")
    def test_search_pagination_params(self, mock_search):
        mock_search.return_value = {
            "count": 0, "page": 2, "page_size": 10,
            "results": [], "facets": {},
        }
        resp = self.client.get("/api/v1/search/", {
            "query": "test", "page": "2", "page_size": "10",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        _, kwargs = mock_search.call_args
        self.assertEqual(kwargs.get("page") or mock_search.call_args[1].get("page"), 2)

    @patch("search.views.execute_search")
    def test_search_page_size_cap(self, mock_search):
        mock_search.return_value = {
            "count": 0, "page": 1, "page_size": 100,
            "results": [], "facets": {},
        }
        resp = self.client.get("/api/v1/search/", {
            "query": "test", "page_size": "500",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        call_kwargs = mock_search.call_args
        # page_size should be capped at 100
        self.assertLessEqual(call_kwargs[1].get("page_size", 100), 100)

    @patch("search.views.execute_search")
    def test_search_with_filters(self, mock_search):
        mock_search.return_value = {
            "count": 0, "page": 1, "page_size": 25,
            "results": [], "facets": {},
        }
        resp = self.client.get("/api/v1/search/", {
            "query": "test",
            "document_type_id": "5",
            "correspondent_id": "3",
            "tag_ids": "1,2",
            "created_after": "2025-01-01",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        call_kwargs = mock_search.call_args[1]
        filters = call_kwargs.get("filters", {})
        self.assertEqual(filters.get("document_type_id"), 5)
        self.assertEqual(filters.get("correspondent_id"), 3)
        self.assertEqual(filters.get("tag_ids"), [1, 2])

    @patch("search.views.execute_search")
    def test_search_permission_filtering(self, mock_search):
        mock_search.return_value = {
            "count": 0, "page": 1, "page_size": 25,
            "results": [], "facets": {},
        }
        resp = self.client.get("/api/v1/search/", {"query": "test"})
        call_kwargs = mock_search.call_args[1]
        self.assertEqual(call_kwargs["user_id"], self.user.id)

    @patch("search.views.execute_search")
    def test_superuser_no_permission_filter(self, mock_search):
        admin = User.objects.create_superuser(username="admin", password="admin!")
        admin_token = Token.objects.create(user=admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {admin_token.key}")
        mock_search.return_value = {
            "count": 0, "page": 1, "page_size": 25,
            "results": [], "facets": {},
        }
        resp = self.client.get("/api/v1/search/", {"query": "test"})
        call_kwargs = mock_search.call_args[1]
        self.assertIsNone(call_kwargs["user_id"])

    def test_search_unauthenticated(self):
        client = APIClient()
        resp = client.get("/api/v1/search/", {"query": "test"})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class SearchAutocompleteViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="acuser", password="pass!")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    @patch("search.views.execute_autocomplete")
    def test_autocomplete(self, mock_ac):
        mock_ac.return_value = [
            {"id": 1, "title": "Invoice 001", "score": 3.5},
        ]
        resp = self.client.get("/api/v1/search/autocomplete/", {"query": "inv"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_autocomplete_short_query(self):
        resp = self.client.get("/api/v1/search/autocomplete/", {"query": "a"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])


class SimilarDocumentsViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="simuser", password="pass!")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    @patch("search.views.execute_more_like_this")
    def test_similar_documents(self, mock_mlt):
        mock_mlt.return_value = [
            {"id": 2, "title": "Similar Doc", "score": 2.1},
        ]
        resp = self.client.get("/api/v1/search/similar/1/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        mock_mlt.assert_called_once()


class SavedViewViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="viewuser", password="pass!")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        self.other_user = User.objects.create_user(username="other", password="pass!")
        self.other_token = Token.objects.create(user=self.other_user)

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_create_saved_view(self):
        resp = self.client.post("/api/v1/saved-views/", {
            "name": "My Invoices",
            "display_mode": "table",
            "filter_rules": [
                {"rule_type": "title_contains", "value": "invoice"},
            ],
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["name"], "My Invoices")
        self.assertEqual(resp.data["owner"], self.user.pk)
        self.assertEqual(len(resp.data["filter_rules"]), 1)

    def test_create_saved_view_with_multiple_rules(self):
        resp = self.client.post("/api/v1/saved-views/", {
            "name": "Complex View",
            "filter_rules": [
                {"rule_type": "title_contains", "value": "invoice"},
                {"rule_type": "has_tags", "value": ""},
                {"rule_type": "created_after", "value": "2025-01-01"},
            ],
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(resp.data["filter_rules"]), 3)

    def test_list_saved_views(self):
        SavedView.objects.create(name="View A", owner=self.user)
        SavedView.objects.create(name="View B", owner=self.user)
        SavedView.objects.create(name="Other View", owner=self.other_user)

        resp = self.client.get("/api/v1/saved-views/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 2)

    def test_get_saved_view_detail(self):
        view = SavedView.objects.create(name="Detail View", owner=self.user)
        SavedViewFilterRule.objects.create(
            saved_view=view, rule_type=RULE_TITLE_CONTAINS, value="test",
        )
        resp = self.client.get(f"/api/v1/saved-views/{view.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["name"], "Detail View")
        self.assertEqual(len(resp.data["filter_rules"]), 1)

    def test_update_saved_view(self):
        view = SavedView.objects.create(name="Old Name", owner=self.user)
        resp = self.client.patch(
            f"/api/v1/saved-views/{view.pk}/",
            {"name": "New Name"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        view.refresh_from_db()
        self.assertEqual(view.name, "New Name")

    def test_update_saved_view_replaces_rules(self):
        view = SavedView.objects.create(name="Rule View", owner=self.user)
        SavedViewFilterRule.objects.create(
            saved_view=view, rule_type=RULE_TITLE_CONTAINS, value="old",
        )
        resp = self.client.patch(
            f"/api/v1/saved-views/{view.pk}/",
            {
                "filter_rules": [
                    {"rule_type": "tag_is", "value": "5"},
                    {"rule_type": "has_tags", "value": ""},
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(view.filter_rules.count(), 2)
        rule_types = set(view.filter_rules.values_list("rule_type", flat=True))
        self.assertIn(RULE_TAG_IS, rule_types)
        self.assertIn(RULE_HAS_TAGS, rule_types)

    def test_delete_saved_view(self):
        view = SavedView.objects.create(name="Deletable", owner=self.user)
        resp = self.client.delete(f"/api/v1/saved-views/{view.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SavedView.objects.filter(pk=view.pk).exists())

    def test_user_isolation(self):
        view = SavedView.objects.create(name="Secret View", owner=self.user)
        self._auth(self.other_token)
        resp = self.client.get(f"/api/v1/saved-views/{view.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_execute_saved_view(self):
        tag = Tag.objects.create(name="Finance", owner=self.user)
        doc = Document.objects.create(
            title="Tagged Doc", owner=self.user, filename="o/tagged.pdf",
        )
        doc.tags.add(tag)
        Document.objects.create(
            title="Untagged Doc", owner=self.user, filename="o/untagged.pdf",
        )

        view = SavedView.objects.create(name="Tagged", owner=self.user)
        SavedViewFilterRule.objects.create(
            saved_view=view, rule_type=RULE_TAG_IS, value=str(tag.pk),
        )

        resp = self.client.get(f"/api/v1/saved-views/{view.pk}/execute/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Tagged Doc")

    def test_dashboard_action(self):
        SavedView.objects.create(
            name="Dashboard View", owner=self.user, show_on_dashboard=True,
        )
        SavedView.objects.create(
            name="Regular View", owner=self.user, show_on_dashboard=False,
        )
        resp = self.client.get("/api/v1/saved-views/dashboard/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["name"], "Dashboard View")

    def test_sidebar_action(self):
        SavedView.objects.create(
            name="Sidebar View", owner=self.user, show_in_sidebar=True,
        )
        SavedView.objects.create(
            name="Hidden View", owner=self.user, show_in_sidebar=False,
        )
        resp = self.client.get("/api/v1/saved-views/sidebar/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["name"], "Sidebar View")

    def test_dashboard_sidebar_user_isolation(self):
        SavedView.objects.create(
            name="Other Dashboard", owner=self.other_user, show_on_dashboard=True,
        )
        resp = self.client.get("/api/v1/saved-views/dashboard/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    def test_unauthenticated_access_denied(self):
        client = APIClient()
        resp = client.get("/api/v1/saved-views/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

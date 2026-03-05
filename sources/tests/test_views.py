"""Tests for source API views."""

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from sources.constants import (
    CONSUMED_ACTION_DELETE,
    MAIL_SECURITY_SSL,
    SOURCE_EMAIL,
    SOURCE_WATCH_FOLDER,
)
from sources.models import MailAccount, MailRule, Source, WatchFolderSource


class SourceViewSetTest(TestCase):
    """Tests for SourceViewSet."""

    def setUp(self):
        self.user = User.objects.create_superuser(
            "admin", "admin@test.com", "adminpass"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.source = Source.objects.create(
            label="Test Source",
            source_type=SOURCE_WATCH_FOLDER,
        )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def test_list_sources(self):
        resp = self.client.get("/api/v1/sources/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)

    def test_list_sources_multiple(self):
        Source.objects.create(label="Second", source_type=SOURCE_EMAIL)
        resp = self.client.get("/api/v1/sources/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 2)

    def test_retrieve_source(self):
        resp = self.client.get(f"/api/v1/sources/{self.source.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["label"], "Test Source")
        self.assertEqual(resp.data["source_type"], SOURCE_WATCH_FOLDER)
        self.assertTrue(resp.data["enabled"])

    def test_create_source(self):
        resp = self.client.post("/api/v1/sources/", {
            "label": "New Source",
            "source_type": "watch_folder",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["label"], "New Source")
        self.assertEqual(resp.data["source_type"], SOURCE_WATCH_FOLDER)

    def test_create_source_email_type(self):
        resp = self.client.post("/api/v1/sources/", {
            "label": "Email Source",
            "source_type": "email",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["source_type"], SOURCE_EMAIL)

    def test_update_source(self):
        resp = self.client.patch(
            f"/api/v1/sources/{self.source.pk}/",
            {"label": "Updated Source"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["label"], "Updated Source")

    def test_update_source_enabled(self):
        resp = self.client.patch(
            f"/api/v1/sources/{self.source.pk}/",
            {"enabled": False},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["enabled"])

    def test_delete_source(self):
        resp = self.client.delete(f"/api/v1/sources/{self.source.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Source.objects.count(), 0)

    def test_delete_nonexistent_source(self):
        resp = self.client.delete("/api/v1/sources/99999/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------------------------------------------------------
    # Watch folder nested action
    # ------------------------------------------------------------------

    def test_create_watch_folder(self):
        resp = self.client.post(
            f"/api/v1/sources/{self.source.pk}/watch-folder/",
            {"path": "/data/consume", "polling_interval": 60},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["path"], "/data/consume")
        self.assertEqual(resp.data["polling_interval"], 60)

    def test_get_watch_folder(self):
        WatchFolderSource.objects.create(
            source=self.source, path="/data/watch",
        )
        resp = self.client.get(
            f"/api/v1/sources/{self.source.pk}/watch-folder/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["path"], "/data/watch")

    def test_get_watch_folder_not_found(self):
        resp = self.client.get(
            f"/api/v1/sources/{self.source.pk}/watch-folder/"
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_watch_folder(self):
        WatchFolderSource.objects.create(
            source=self.source, path="/data/old",
        )
        resp = self.client.patch(
            f"/api/v1/sources/{self.source.pk}/watch-folder/",
            {"path": "/data/new", "consumed_action": CONSUMED_ACTION_DELETE},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["path"], "/data/new")
        self.assertEqual(resp.data["consumed_action"], CONSUMED_ACTION_DELETE)

    def test_create_watch_folder_with_consumed_directory(self):
        resp = self.client.post(
            f"/api/v1/sources/{self.source.pk}/watch-folder/",
            {
                "path": "/data/incoming",
                "consumed_directory": "/data/consumed",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["consumed_directory"], "/data/consumed")

    # ------------------------------------------------------------------
    # Source serializer fields
    # ------------------------------------------------------------------

    def test_source_response_contains_timestamps(self):
        resp = self.client.get(f"/api/v1/sources/{self.source.pk}/")
        self.assertIn("created_at", resp.data)
        self.assertIn("updated_at", resp.data)


class MailAccountViewSetTest(TestCase):
    """Tests for MailAccountViewSet."""

    def setUp(self):
        self.user = User.objects.create_superuser(
            "admin", "admin@test.com", "adminpass"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.account = MailAccount.objects.create(
            name="Test Mail",
            imap_server="imap.test.com",
            username="test@test.com",
            password="secret",
        )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def test_list_accounts(self):
        resp = self.client.get("/api/v1/mail-accounts/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)

    def test_list_accounts_multiple(self):
        MailAccount.objects.create(
            name="Second",
            imap_server="imap2.test.com",
            username="second@test.com",
        )
        resp = self.client.get("/api/v1/mail-accounts/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 2)

    def test_retrieve_account(self):
        resp = self.client.get(f"/api/v1/mail-accounts/{self.account.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["name"], "Test Mail")
        self.assertEqual(resp.data["imap_server"], "imap.test.com")

    def test_create_account(self):
        resp = self.client.post("/api/v1/mail-accounts/", {
            "name": "New Mail",
            "imap_server": "imap.example.com",
            "port": 993,
            "security": "ssl",
            "username": "user@example.com",
            "password": "pass",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["name"], "New Mail")

    def test_create_account_minimal(self):
        resp = self.client.post("/api/v1/mail-accounts/", {
            "name": "Minimal",
            "imap_server": "imap.minimal.com",
            "username": "min@minimal.com",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["port"], 993)
        self.assertEqual(resp.data["security"], MAIL_SECURITY_SSL)

    def test_update_account(self):
        resp = self.client.patch(
            f"/api/v1/mail-accounts/{self.account.pk}/",
            {"name": "Updated Mail"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["name"], "Updated Mail")

    def test_delete_account(self):
        resp = self.client.delete(f"/api/v1/mail-accounts/{self.account.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(MailAccount.objects.count(), 0)

    # ------------------------------------------------------------------
    # Password security
    # ------------------------------------------------------------------

    def test_password_not_in_response(self):
        resp = self.client.get(f"/api/v1/mail-accounts/{self.account.pk}/")
        self.assertNotIn("password", resp.data)

    def test_password_not_in_list_response(self):
        resp = self.client.get("/api/v1/mail-accounts/")
        for item in resp.data["results"]:
            self.assertNotIn("password", item)

    def test_password_can_be_set_on_create(self):
        resp = self.client.post("/api/v1/mail-accounts/", {
            "name": "With Password",
            "imap_server": "imap.pass.com",
            "username": "pass@pass.com",
            "password": "my-secret-pass",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        account = MailAccount.objects.get(pk=resp.data["id"])
        self.assertEqual(account.password, "my-secret-pass")
        self.assertNotIn("password", resp.data)

    # ------------------------------------------------------------------
    # Computed fields
    # ------------------------------------------------------------------

    def test_rule_count_field(self):
        resp = self.client.get(f"/api/v1/mail-accounts/{self.account.pk}/")
        self.assertEqual(resp.data["rule_count"], 0)

    def test_rule_count_with_rules(self):
        MailRule.objects.create(name="R1", account=self.account)
        MailRule.objects.create(name="R2", account=self.account)
        resp = self.client.get(f"/api/v1/mail-accounts/{self.account.pk}/")
        self.assertEqual(resp.data["rule_count"], 2)


class MailRuleViewSetTest(TestCase):
    """Tests for MailRuleViewSet."""

    def setUp(self):
        self.user = User.objects.create_superuser(
            "admin", "admin@test.com", "adminpass"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.account = MailAccount.objects.create(
            name="Test",
            imap_server="imap.test.com",
            username="test@test.com",
            password="pass",
        )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def test_list_rules(self):
        MailRule.objects.create(name="Rule 1", account=self.account)
        resp = self.client.get(
            f"/api/v1/mail-accounts/{self.account.pk}/rules/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_list_rules_empty(self):
        resp = self.client.get(
            f"/api/v1/mail-accounts/{self.account.pk}/rules/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    def test_list_rules_multiple(self):
        MailRule.objects.create(name="Rule 1", account=self.account)
        MailRule.objects.create(name="Rule 2", account=self.account)
        resp = self.client.get(
            f"/api/v1/mail-accounts/{self.account.pk}/rules/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

    def test_list_rules_scoped_to_account(self):
        """Rules from other accounts should not appear."""
        other_account = MailAccount.objects.create(
            name="Other",
            imap_server="imap.other.com",
            username="other@test.com",
        )
        MailRule.objects.create(name="Other Rule", account=other_account)
        MailRule.objects.create(name="My Rule", account=self.account)
        resp = self.client.get(
            f"/api/v1/mail-accounts/{self.account.pk}/rules/"
        )
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["name"], "My Rule")

    def test_create_rule(self):
        resp = self.client.post(
            f"/api/v1/mail-accounts/{self.account.pk}/rules/",
            {"name": "New Rule", "folder": "INBOX"},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["name"], "New Rule")
        self.assertEqual(resp.data["folder"], "INBOX")

    def test_create_rule_with_filters(self):
        resp = self.client.post(
            f"/api/v1/mail-accounts/{self.account.pk}/rules/",
            {
                "name": "Filtered Rule",
                "folder": "INBOX",
                "filter_from": "billing@corp.com",
                "filter_subject": "Invoice*",
                "filter_attachment_filename": "*.pdf",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["filter_from"], "billing@corp.com")
        self.assertEqual(resp.data["filter_attachment_filename"], "*.pdf")

    def test_create_rule_sets_account(self):
        """The account should be set from the URL, not the request body."""
        resp = self.client.post(
            f"/api/v1/mail-accounts/{self.account.pk}/rules/",
            {"name": "Auto Account"},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        rule = MailRule.objects.get(pk=resp.data["id"])
        self.assertEqual(rule.account_id, self.account.pk)

    def test_retrieve_rule(self):
        rule = MailRule.objects.create(
            name="Detail Rule", account=self.account, folder="INBOX",
        )
        resp = self.client.get(
            f"/api/v1/mail-accounts/{self.account.pk}/rules/{rule.pk}/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["name"], "Detail Rule")

    def test_update_rule(self):
        rule = MailRule.objects.create(name="Old", account=self.account)
        resp = self.client.patch(
            f"/api/v1/mail-accounts/{self.account.pk}/rules/{rule.pk}/",
            {"name": "Updated"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["name"], "Updated")

    def test_delete_rule(self):
        rule = MailRule.objects.create(name="Del", account=self.account)
        resp = self.client.delete(
            f"/api/v1/mail-accounts/{self.account.pk}/rules/{rule.pk}/"
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(MailRule.objects.count(), 0)


class UnauthenticatedSourceAccessTest(TestCase):
    """Tests that unauthenticated users cannot access source endpoints."""

    def test_sources_require_auth(self):
        client = APIClient()
        resp = client.get("/api/v1/sources/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_mail_accounts_require_auth(self):
        client = APIClient()
        resp = client.get("/api/v1/mail-accounts/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_source_detail_requires_auth(self):
        source = Source.objects.create(
            label="Auth Test", source_type=SOURCE_WATCH_FOLDER,
        )
        client = APIClient()
        resp = client.get(f"/api/v1/sources/{source.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_mail_account_detail_requires_auth(self):
        account = MailAccount.objects.create(
            name="Auth Test",
            imap_server="imap.test.com",
            username="test@test.com",
        )
        client = APIClient()
        resp = client.get(f"/api/v1/mail-accounts/{account.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_mail_rules_require_auth(self):
        account = MailAccount.objects.create(
            name="Auth Test",
            imap_server="imap.test.com",
            username="test@test.com",
        )
        client = APIClient()
        resp = client.get(f"/api/v1/mail-accounts/{account.pk}/rules/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_source_requires_auth(self):
        client = APIClient()
        resp = client.post("/api/v1/sources/", {
            "label": "Hack",
            "source_type": "watch_folder",
        })
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_mail_account_requires_auth(self):
        client = APIClient()
        resp = client.post("/api/v1/mail-accounts/", {
            "name": "Hack",
            "imap_server": "imap.hack.com",
            "username": "hack@hack.com",
        })
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

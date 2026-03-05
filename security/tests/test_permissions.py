"""Tests for permission classes and utilities."""

from unittest.mock import MagicMock

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from guardian.shortcuts import assign_perm

from documents.models import Document
from security.permissions import (
    DocVaultObjectPermissions,
    get_objects_for_user_with_ownership,
    set_object_permissions,
)


class DocVaultObjectPermissionsTest(TestCase):
    """Tests for the custom object permission class."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.owner = User.objects.create_user("owner", password="testpass123!")
        self.other = User.objects.create_user("other", password="testpass123!")
        self.admin = User.objects.create_superuser("admin", password="testpass123!")
        self.doc = Document.objects.create(
            title="Test Doc",
            filename="test.pdf",
            owner=self.owner,
        )
        self.perm = DocVaultObjectPermissions()
        # Mock view with queryset (required by DjangoObjectPermissions)
        self.view = MagicMock()
        self.view.get_queryset.return_value = Document.objects.all()

    def _make_request(self, user, method="GET"):
        request = getattr(self.factory, method.lower())("/")
        request.user = user
        return request

    def test_superuser_always_allowed(self):
        request = self._make_request(self.admin)
        self.assertTrue(self.perm.has_object_permission(request, self.view, self.doc))

    def test_owner_always_allowed(self):
        request = self._make_request(self.owner)
        self.assertTrue(self.perm.has_object_permission(request, self.view, self.doc))

    def test_non_owner_without_permission_denied(self):
        from django.http import Http404

        request = self._make_request(self.other)
        # DRF's DjangoObjectPermissions raises Http404 for denied users
        with self.assertRaises(Http404):
            self.perm.has_object_permission(request, self.view, self.doc)

    def test_non_owner_with_guardian_permission_allowed(self):
        assign_perm("documents.view_document", self.other, self.doc)
        request = self._make_request(self.other)
        self.assertTrue(self.perm.has_object_permission(request, self.view, self.doc))


class GetObjectsForUserTest(TestCase):
    """Tests for get_objects_for_user_with_ownership."""

    def setUp(self):
        self.owner = User.objects.create_user("owner", password="testpass123!")
        self.other = User.objects.create_user("other", password="testpass123!")
        self.admin = User.objects.create_superuser("admin", password="testpass123!")

        self.owned_doc = Document.objects.create(
            title="Owned Doc", filename="owned.pdf", owner=self.owner,
        )
        self.other_doc = Document.objects.create(
            title="Other Doc", filename="other.pdf", owner=self.other,
        )
        self.shared_doc = Document.objects.create(
            title="Shared Doc", filename="shared.pdf", owner=self.other,
        )

    def test_superuser_sees_all(self):
        qs = get_objects_for_user_with_ownership(
            self.admin, "documents.view_document", Document.objects.all()
        )
        self.assertEqual(qs.count(), 3)

    def test_owner_sees_owned(self):
        qs = get_objects_for_user_with_ownership(
            self.owner, "documents.view_document", Document.objects.all()
        )
        self.assertIn(self.owned_doc, qs)
        self.assertNotIn(self.other_doc, qs)

    def test_owner_sees_owned_plus_shared(self):
        assign_perm("documents.view_document", self.owner, self.shared_doc)
        qs = get_objects_for_user_with_ownership(
            self.owner, "documents.view_document", Document.objects.all()
        )
        self.assertEqual(qs.count(), 2)
        self.assertIn(self.owned_doc, qs)
        self.assertIn(self.shared_doc, qs)

    def test_no_duplicates(self):
        # Owner has both ownership and explicit permission
        assign_perm("documents.view_document", self.owner, self.owned_doc)
        qs = get_objects_for_user_with_ownership(
            self.owner, "documents.view_document", Document.objects.all()
        )
        self.assertEqual(qs.count(), 1)


class SetObjectPermissionsTest(TestCase):
    """Tests for the set_object_permissions utility."""

    def setUp(self):
        self.user1 = User.objects.create_user("user1", password="testpass123!")
        self.user2 = User.objects.create_user("user2", password="testpass123!")
        self.doc = Document.objects.create(
            title="Test Doc", filename="test.pdf",
        )

    def test_set_permissions_for_users(self):
        set_object_permissions(self.doc, {
            "view": {"users": [self.user1, self.user2]},
        })
        self.assertTrue(self.user1.has_perm("documents.view_document", self.doc))
        self.assertTrue(self.user2.has_perm("documents.view_document", self.doc))

    def test_set_permissions_by_user_id(self):
        set_object_permissions(self.doc, {
            "view": {"users": [self.user1.pk]},
        })
        self.assertTrue(self.user1.has_perm("documents.view_document", self.doc))

    def test_set_multiple_permission_types(self):
        set_object_permissions(self.doc, {
            "view": {"users": [self.user1]},
            "change": {"users": [self.user1]},
        })
        self.assertTrue(self.user1.has_perm("documents.view_document", self.doc))
        self.assertTrue(self.user1.has_perm("documents.change_document", self.doc))

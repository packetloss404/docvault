"""Tests for security models."""

from django.contrib.auth.models import Group, User
from django.db import IntegrityError
from django.test import TestCase

from security.models import Permission, Role


class PermissionModelTest(TestCase):
    """Tests for Permission model."""

    def test_create_permission(self):
        perm = Permission.objects.create(
            namespace="custom", codename="do_thing", name="Can do a thing"
        )
        self.assertEqual(str(perm), "custom.do_thing")

    def test_full_codename(self):
        perm = Permission.objects.create(
            namespace="custom", codename="do_thing", name="Can do a thing"
        )
        self.assertEqual(perm.full_codename, "custom.do_thing")

    def test_unique_together(self):
        Permission.objects.create(
            namespace="custom", codename="unique_test", name="Test"
        )
        with self.assertRaises(IntegrityError):
            Permission.objects.create(
                namespace="custom", codename="unique_test", name="Duplicate"
            )

    def test_same_codename_different_namespace(self):
        Permission.objects.create(namespace="ns_a", codename="action", name="A action")
        Permission.objects.create(namespace="ns_b", codename="action", name="B action")
        self.assertEqual(
            Permission.objects.filter(codename="action").count(), 2
        )

    def test_initial_permissions_exist(self):
        """Data migration should have created initial permissions."""
        self.assertTrue(
            Permission.objects.filter(namespace="documents", codename="view_document").exists()
        )
        self.assertTrue(
            Permission.objects.filter(namespace="security", codename="manage_user").exists()
        )

    def test_ordering(self):
        perms = list(Permission.objects.values_list("namespace", flat=True)[:4])
        self.assertEqual(perms, sorted(perms))


class RoleModelTest(TestCase):
    """Tests for Role model."""

    def setUp(self):
        self.perm_view = Permission.objects.get(namespace="documents", codename="view_document")
        self.perm_add = Permission.objects.get(namespace="documents", codename="add_document")
        self.group = Group.objects.create(name="Editors")

    def test_create_role(self):
        role = Role.objects.create(name="Viewer")
        self.assertEqual(str(role), "Viewer")

    def test_unique_name(self):
        Role.objects.create(name="Viewer")
        with self.assertRaises(IntegrityError):
            Role.objects.create(name="Viewer")

    def test_has_permission(self):
        role = Role.objects.create(name="Viewer")
        role.permissions.add(self.perm_view)
        self.assertTrue(role.has_permission("documents", "view_document"))
        self.assertFalse(role.has_permission("documents", "add_document"))

    def test_assign_to_group(self):
        role = Role.objects.create(name="Editor")
        role.permissions.add(self.perm_view, self.perm_add)
        role.groups.add(self.group)
        self.assertIn(self.group, role.groups.all())

    def test_get_users(self):
        role = Role.objects.create(name="Editor")
        role.groups.add(self.group)
        user = User.objects.create_user("testuser", password="testpass123!")
        user.groups.add(self.group)
        self.assertIn(user, role.get_users())

    def test_get_users_empty(self):
        role = Role.objects.create(name="Empty")
        self.assertEqual(role.get_users().count(), 0)

    def test_auditable_fields(self):
        role = Role.objects.create(name="Test")
        self.assertIsNotNone(role.created_at)
        self.assertIsNotNone(role.updated_at)

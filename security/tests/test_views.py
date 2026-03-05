"""Tests for security API views."""

from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from security.models import Permission, Role


class AuthViewTests(TestCase):
    """Tests for authentication endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123!",
        )

    def test_register(self):
        resp = self.client.post("/api/v1/auth/register/", {
            "username": "newuser",
            "email": "new@example.com",
            "password": "newpass123!",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("token", resp.data)
        self.assertIn("user_id", resp.data)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_weak_password(self):
        resp = self.client.post("/api/v1/auth/register/", {
            "username": "newuser",
            "email": "new@example.com",
            "password": "123",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username(self):
        resp = self.client.post("/api/v1/auth/register/", {
            "username": "testuser",
            "email": "other@example.com",
            "password": "newpass123!",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login(self):
        resp = self.client.post("/api/v1/auth/login/", {
            "username": "testuser",
            "password": "testpass123!",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("token", resp.data)
        self.assertEqual(resp.data["username"], "testuser")

    def test_login_wrong_password(self):
        resp = self.client.post("/api/v1/auth/login/", {
            "username": "testuser",
            "password": "wrongpass",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_nonexistent_user(self):
        resp = self.client.post("/api/v1/auth/login/", {
            "username": "nobody",
            "password": "whatever",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout(self):
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        resp = self.client.post("/api/v1/auth/logout/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_logout_unauthenticated(self):
        resp = self.client.post("/api/v1/auth/logout/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_get(self):
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        resp = self.client.get("/api/v1/auth/profile/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["username"], "testuser")
        self.assertEqual(resp.data["email"], "test@example.com")

    def test_profile_update(self):
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        resp = self.client.patch("/api/v1/auth/profile/", {
            "first_name": "Test",
            "last_name": "User",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Test")

    def test_change_password(self):
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        resp = self.client.post("/api/v1/auth/change-password/", {
            "old_password": "testpass123!",
            "new_password": "newpass456!",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("token", resp.data)
        # Old token should be invalid
        self.assertFalse(Token.objects.filter(key=token.key).exists())
        # User can login with new password
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass456!"))

    def test_change_password_wrong_old(self):
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        resp = self.client.post("/api/v1/auth/change-password/", {
            "old_password": "wrongold",
            "new_password": "newpass456!",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_token(self):
        old_token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {old_token.key}")
        resp = self.client.post("/api/v1/auth/token/")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("token", resp.data)
        self.assertNotEqual(resp.data["token"], old_token.key)

    def test_token_auth(self):
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        resp = self.client.get("/api/v1/auth/profile/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_invalid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token invalidtoken123")
        resp = self.client.get("/api/v1/auth/profile/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class UserViewSetTests(TestCase):
    """Tests for user management endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123!"
        )
        self.regular = User.objects.create_user(
            username="regular", email="reg@example.com", password="regpass123!"
        )
        self.admin_token = Token.objects.create(user=self.admin)
        self.regular_token = Token.objects.create(user=self.regular)

    def test_list_users_as_admin(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        resp = self.client.get("/api/v1/users/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 2)

    def test_list_users_as_regular_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.regular_token.key}")
        resp = self.client.get("/api/v1/users/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_user_as_admin(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        resp = self.client.post("/api/v1/users/", {
            "username": "newuser",
            "email": "new@example.com",
            "password": "newpass123!",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        new_user = User.objects.get(username="newuser")
        self.assertTrue(new_user.check_password("newpass123!"))

    def test_update_user_as_admin(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        resp = self.client.patch(f"/api/v1/users/{self.regular.pk}/", {
            "first_name": "Updated",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.regular.refresh_from_db()
        self.assertEqual(self.regular.first_name, "Updated")


class GroupViewSetTests(TestCase):
    """Tests for group management endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123!"
        )
        self.token = Token.objects.create(user=self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_create_group(self):
        resp = self.client.post("/api/v1/groups/", {"name": "Editors"})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Group.objects.filter(name="Editors").exists())

    def test_list_groups(self):
        Group.objects.create(name="Editors")
        Group.objects.create(name="Viewers")
        resp = self.client.get("/api/v1/groups/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 2)

    def test_group_user_count(self):
        group = Group.objects.create(name="Editors")
        user = User.objects.create_user("editor1", password="testpass123!")
        user.groups.add(group)
        resp = self.client.get(f"/api/v1/groups/{group.pk}/")
        self.assertEqual(resp.data["user_count"], 1)


class RoleViewSetTests(TestCase):
    """Tests for role management endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123!"
        )
        self.token = Token.objects.create(user=self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_create_role(self):
        resp = self.client.post("/api/v1/roles/", {
            "name": "Document Viewer",
            "description": "Can view documents only",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Role.objects.filter(name="Document Viewer").exists())

    def test_list_roles(self):
        Role.objects.create(name="Viewer")
        Role.objects.create(name="Editor")
        resp = self.client.get("/api/v1/roles/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 2)

    def test_create_role_with_permissions(self):
        perm = Permission.objects.get(namespace="documents", codename="view_document")
        resp = self.client.post("/api/v1/roles/", {
            "name": "Viewer",
            "permission_ids": [perm.pk],
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        role = Role.objects.get(name="Viewer")
        self.assertIn(perm, role.permissions.all())

    def test_permissions_list(self):
        resp = self.client.get("/api/v1/permissions/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreater(len(resp.data), 0)
        # Check structure
        self.assertIn("namespace", resp.data[0])
        self.assertIn("codename", resp.data[0])

import pytest
from django.contrib.auth.models import Group, User

from documents.models import Document
from security.authentication import RolePermissionBackend
from security.models import Permission, Role
from security.permissions import get_objects_for_user_with_ownership


@pytest.mark.django_db
def test_roles_grant_and_revoke_django_permissions_without_stale_cache(settings):
    settings.AUTHENTICATION_BACKENDS = [
        *settings.AUTHENTICATION_BACKENDS, "security.authentication.RolePermissionBackend",
    ]
    owner = User.objects.create_user("role-owner")
    user = User.objects.create_user("role-reader")
    document = Document.objects.create(owner=owner, title="Private")
    group = Group.objects.create(name="Read-only role")
    role = Role.objects.create(name="Readers")
    permission = Permission.objects.get(namespace="documents", codename="view_document")
    role.permissions.add(permission)
    role.groups.add(group)
    assert not user.has_perm("documents.view_document", document)

    user.groups.add(group)
    assert user.has_perm("documents.view_document", document)
    assert not user.has_perm("documents.change_document", document)
    assert get_objects_for_user_with_ownership(user, "documents.view_document", Document.objects.all()).filter(
        pk=document.pk,
    ).exists()

    role.permissions.clear()
    assert not user.has_perm("documents.view_document", document)
    assert not get_objects_for_user_with_ownership(user, "documents.view_document", Document.objects.all()).exists()


@pytest.mark.django_db
def test_inactive_user_cannot_use_role_permissions():
    user = User.objects.create_user("inactive-role-reader", is_active=False)
    assert RolePermissionBackend().get_all_permissions(user) == set()

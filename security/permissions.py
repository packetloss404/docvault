"""DRF permission classes for DocVault."""

from rest_framework.permissions import BasePermission, DjangoObjectPermissions

from guardian.shortcuts import get_objects_for_user


class DocVaultObjectPermissions(DjangoObjectPermissions):
    """
    Custom permission class that checks (in order):
    1. Is user superuser? -> Allow all
    2. Is user the object owner? -> Allow all
    3. Does user have explicit object permission (guardian)? -> Check
    4. Default: Deny

    Note: has_permission() allows any authenticated user through.
    Actual access control is handled by queryset filtering (in get_queryset)
    and has_object_permission() for detail views.
    """

    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }

    def has_permission(self, request, view):
        # Allow any authenticated user through at the view level.
        # Object-level checks (ownership, guardian) are enforced in
        # has_object_permission and via queryset filtering.
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        # Owner shortcut: owners always have full access
        if hasattr(obj, "owner") and obj.owner == request.user:
            return True

        # Fall through to guardian object permission check
        return super().has_object_permission(request, view, obj)


class IsAdminOrReadOnly(BasePermission):
    """Allow read access to any authenticated user, write access only to admins."""

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_staff


class IsOwnerOrAdmin(BasePermission):
    """Allow access only to the object owner or admin users."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.is_staff:
            return True
        if hasattr(obj, "owner"):
            return obj.owner == request.user
        return False


def get_objects_for_user_with_ownership(user, perm, queryset):
    """
    Return objects a user can access, including owned objects.

    Combines guardian object permissions with ownership shortcut.
    """
    if user.is_superuser:
        return queryset

    # Objects the user owns
    if hasattr(queryset.model, "owner"):
        owned = queryset.filter(owner=user)
    else:
        owned = queryset.none()

    # Objects the user has explicit guardian permissions on
    permitted = get_objects_for_user(
        user,
        perm,
        queryset,
        accept_global_perms=True,
        with_superuser=False,
    )

    return (owned | permitted).distinct()


def set_object_permissions(obj, permissions_dict):
    """
    Set object-level permissions for a given object.

    permissions_dict format:
    {
        'view': {'users': [user1, user2], 'groups': [group1]},
        'change': {'users': [user1], 'groups': []},
    }
    """
    from django.contrib.auth.models import User, Group

    from guardian.shortcuts import assign_perm, remove_perm

    app_label = obj._meta.app_label
    model_name = obj._meta.model_name

    for action, targets in permissions_dict.items():
        perm = f"{app_label}.{action}_{model_name}"

        for user in targets.get("users", []):
            if isinstance(user, int):
                user = User.objects.get(pk=user)
            assign_perm(perm, user, obj)

        for group in targets.get("groups", []):
            if isinstance(group, int):
                group = Group.objects.get(pk=group)
            assign_perm(perm, group, obj)

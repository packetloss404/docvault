"""Permission and Role models for the security module."""

from django.contrib.auth.models import Group
from django.db import models

from core.models import AuditableModel


class Permission(models.Model):
    """
    System-level permission definition.

    Uses a namespace/codename pattern for clear organization:
    e.g., documents.view_document, security.manage_user
    """

    namespace = models.CharField(max_length=64, help_text="Module namespace (e.g., 'documents').")
    codename = models.CharField(max_length=64, help_text="Permission codename (e.g., 'view_document').")
    name = models.CharField(max_length=256, help_text="Human-readable description.")

    class Meta:
        unique_together = [["namespace", "codename"]]
        ordering = ["namespace", "codename"]
        verbose_name = "permission"
        verbose_name_plural = "permissions"

    def __str__(self):
        return f"{self.namespace}.{self.codename}"

    @property
    def full_codename(self):
        return f"{self.namespace}.{self.codename}"


class Role(AuditableModel):
    """
    Collection of permissions assigned to groups.

    Roles provide a layer between permissions and groups:
    Permission -> Role -> Group -> User
    """

    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True, default="")
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles")
    groups = models.ManyToManyField(Group, blank=True, related_name="roles")

    class Meta:
        ordering = ["name"]
        verbose_name = "role"
        verbose_name_plural = "roles"

    def __str__(self):
        return self.name

    def has_permission(self, namespace, codename):
        """Check if this role grants a specific permission."""
        return self.permissions.filter(namespace=namespace, codename=codename).exists()

    def get_users(self):
        """Get all users who have this role via their groups."""
        from django.contrib.auth.models import User

        return User.objects.filter(groups__in=self.groups.all()).distinct()

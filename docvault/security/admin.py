from django.contrib import admin

from .models import Permission, Role


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ["namespace", "codename", "name"]
    list_filter = ["namespace"]
    search_fields = ["codename", "name"]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "description", "permission_count", "group_count"]
    search_fields = ["name"]
    filter_horizontal = ["permissions", "groups"]

    def permission_count(self, obj):
        return obj.permissions.count()

    def group_count(self, obj):
        return obj.groups.count()

"""Create initial system permissions."""

from django.db import migrations

INITIAL_PERMISSIONS = [
    ("documents", "view_document", "Can view documents"),
    ("documents", "add_document", "Can add documents"),
    ("documents", "change_document", "Can change documents"),
    ("documents", "delete_document", "Can delete documents"),
    ("documents", "download_document", "Can download documents"),
    ("documents", "share_document", "Can share documents"),
    ("documents", "view_documenttype", "Can view document types"),
    ("documents", "manage_documenttype", "Can manage document types"),
    ("security", "view_user", "Can view users"),
    ("security", "manage_user", "Can manage users"),
    ("security", "view_group", "Can view groups"),
    ("security", "manage_group", "Can manage groups"),
    ("security", "view_role", "Can view roles"),
    ("security", "manage_role", "Can manage roles"),
    ("security", "view_permission", "Can view permissions"),
    ("security", "view_auditlog", "Can view audit logs"),
]


def create_permissions(apps, schema_editor):
    Permission = apps.get_model("security", "Permission")
    for namespace, codename, name in INITIAL_PERMISSIONS:
        Permission.objects.get_or_create(
            namespace=namespace,
            codename=codename,
            defaults={"name": name},
        )


def remove_permissions(apps, schema_editor):
    Permission = apps.get_model("security", "Permission")
    for namespace, codename, _ in INITIAL_PERMISSIONS:
        Permission.objects.filter(namespace=namespace, codename=codename).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("security", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_permissions, remove_permissions),
    ]

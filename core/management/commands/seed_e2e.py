"""Create accounts only inside the disposable acceptance stack."""

import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from security.models import OTPDevice


class Command(BaseCommand):
    help = "Create the disposable E2E administrator and regular user. Never run in production."

    def handle(self, *args, **options):
        if os.environ.get("DOCVAULT_E2E") != "1" or settings.SETTINGS_MODULE != "docvault.settings.e2e":
            raise CommandError("Refusing to seed accounts outside docvault.settings.e2e.")
        password = os.environ.get("E2E_ADMIN_PASSWORD", "E2e-only-password-123!")
        accounts = [("e2e-admin", True), ("e2e-user", False)]
        for suite in ("browser", "domain", "platform"):
            accounts.extend(((f"e2e-{suite}-admin", True), (f"e2e-{suite}-user", False)))
        for username, is_admin in accounts:
            user, _ = User.objects.get_or_create(username=username)
            user.email = f"{username}@example.test"
            user.is_active = True
            user.is_staff = is_admin
            user.is_superuser = is_admin
            user.set_password(password)
            user.save()
            OTPDevice.objects.filter(user=user).delete()
            if not is_admin:
                user.groups.clear()
                user.user_permissions.clear()
        self.stdout.write(self.style.SUCCESS("Isolated acceptance accounts are ready."))

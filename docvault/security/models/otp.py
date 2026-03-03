"""OTP device model for two-factor authentication."""

import secrets

from django.conf import settings
from django.db import models


class OTPDevice(models.Model):
    """TOTP device for two-factor authentication."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="otp_device",
    )
    secret = models.CharField(max_length=64)
    confirmed = models.BooleanField(
        default=False,
        help_text="Whether the device has been confirmed with a valid OTP code.",
    )
    backup_codes = models.JSONField(
        default=list,
        blank=True,
        help_text="Hashed backup codes for account recovery.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "OTP device"
        verbose_name_plural = "OTP devices"

    def __str__(self):
        status = "confirmed" if self.confirmed else "pending"
        return f"OTP({self.user.username}, {status})"

    @staticmethod
    def generate_backup_codes(count=8):
        """Generate a set of backup codes."""
        return [secrets.token_hex(4) for _ in range(count)]

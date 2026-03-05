"""Audit log model for tracking security-relevant events."""

from django.conf import settings
from django.db import models


class AuditLogEntry(models.Model):
    """Records security-relevant actions in the system."""

    ACTION_LOGIN = "login"
    ACTION_LOGOUT = "logout"
    ACTION_LOGIN_FAILED = "login_failed"
    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_DELETE = "delete"
    ACTION_DOWNLOAD = "download"
    ACTION_SIGN = "sign"
    ACTION_VERIFY = "verify"
    ACTION_OTP_SETUP = "otp_setup"
    ACTION_OTP_DISABLE = "otp_disable"
    ACTION_PASSWORD_CHANGE = "password_change"
    ACTION_PERMISSION_CHANGE = "permission_change"

    ACTION_CHOICES = [
        (ACTION_LOGIN, "Login"),
        (ACTION_LOGOUT, "Logout"),
        (ACTION_LOGIN_FAILED, "Login Failed"),
        (ACTION_CREATE, "Create"),
        (ACTION_UPDATE, "Update"),
        (ACTION_DELETE, "Delete"),
        (ACTION_DOWNLOAD, "Download"),
        (ACTION_SIGN, "Sign"),
        (ACTION_VERIFY, "Verify"),
        (ACTION_OTP_SETUP, "OTP Setup"),
        (ACTION_OTP_DISABLE, "OTP Disable"),
        (ACTION_PASSWORD_CHANGE, "Password Change"),
        (ACTION_PERMISSION_CHANGE, "Permission Change"),
    ]

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_log_entries",
    )
    action = models.CharField(max_length=32, choices=ACTION_CHOICES, db_index=True)
    model_type = models.CharField(
        max_length=64, blank=True, default="",
        help_text="Model class name (e.g., 'Document', 'User').",
        db_index=True,
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    detail = models.TextField(blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True, default="")

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "audit log entry"
        verbose_name_plural = "audit log entries"
        indexes = [
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["action", "timestamp"]),
        ]

    def __str__(self):
        username = self.user.username if self.user else "anonymous"
        return f"[{self.timestamp}] {username}: {self.action} {self.model_type}"


def log_audit_event(*, user=None, action, model_type="", object_id=None, detail="",
                    ip_address=None, user_agent=""):
    """Helper to create an audit log entry."""
    return AuditLogEntry.objects.create(
        user=user,
        action=action,
        model_type=model_type,
        object_id=object_id,
        detail=detail,
        ip_address=ip_address,
        user_agent=user_agent,
    )

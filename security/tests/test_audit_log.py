"""Tests for the audit log model and helper."""

import pytest
from django.contrib.auth.models import User

from security.models import AuditLogEntry, log_audit_event


@pytest.fixture
def user(db):
    return User.objects.create_user("audituser", password="testpass123!")


@pytest.mark.django_db
class TestLogAuditEvent:
    """Tests for the log_audit_event helper function."""

    def test_creates_entry(self, user):
        entry = log_audit_event(
            user=user,
            action=AuditLogEntry.ACTION_LOGIN,
            detail="User logged in",
            ip_address="10.0.0.1",
            user_agent="Mozilla/5.0",
        )
        assert entry.pk is not None
        assert entry.user == user
        assert entry.action == "login"
        assert entry.detail == "User logged in"
        assert entry.ip_address == "10.0.0.1"

    def test_creates_anonymous_entry(self):
        entry = log_audit_event(
            user=None,
            action=AuditLogEntry.ACTION_LOGIN_FAILED,
            detail="Anonymous failed login",
        )
        assert entry.pk is not None
        assert entry.user is None


@pytest.mark.django_db
class TestAuditLogEntryModel:
    """Tests for the AuditLogEntry model."""

    def test_filter_by_action(self, user):
        log_audit_event(user=user, action="login")
        log_audit_event(user=user, action="create")
        log_audit_event(user=user, action="login")

        assert AuditLogEntry.objects.filter(action="login").count() == 2
        assert AuditLogEntry.objects.filter(action="create").count() == 1

    def test_filter_by_user(self, user):
        other = User.objects.create_user("otheruser", password="pass123!")
        log_audit_event(user=user, action="login")
        log_audit_event(user=other, action="login")

        assert AuditLogEntry.objects.filter(user=user).count() == 1
        assert AuditLogEntry.objects.filter(user=other).count() == 1

    def test_str_representation(self, user):
        entry = log_audit_event(
            user=user,
            action=AuditLogEntry.ACTION_LOGIN,
            model_type="User",
        )
        s = str(entry)
        assert "audituser" in s
        assert "login" in s
        assert "User" in s

    def test_str_representation_anonymous(self):
        entry = log_audit_event(user=None, action=AuditLogEntry.ACTION_LOGIN_FAILED)
        s = str(entry)
        assert "anonymous" in s

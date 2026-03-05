"""Tests for the portal app Celery tasks."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from portal.constants import (
    REQUEST_EXPIRED,
    REQUEST_PARTIALLY_FULFILLED,
    REQUEST_PENDING,
)
from portal.models import DocumentRequest, PortalConfig
from portal.tasks import (
    check_deadline_reminders,
    expire_overdue_requests,
    send_deadline_reminder,
    send_request_email,
)

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def portal(user):
    return PortalConfig.objects.create(
        name="Test Portal",
        slug="task-test-portal",
        is_active=True,
        created_by=user,
    )


@pytest.fixture
def pending_request(portal):
    return DocumentRequest.objects.create(
        portal=portal,
        title="Pending Request",
        assignee_email="person@example.com",
        assignee_name="Test Person",
        status=REQUEST_PENDING,
        deadline=timezone.now() + timedelta(days=7),
    )


@pytest.fixture
def overdue_request(portal):
    return DocumentRequest.objects.create(
        portal=portal,
        title="Overdue Request",
        assignee_email="late@example.com",
        assignee_name="Late Person",
        status=REQUEST_PENDING,
        deadline=timezone.now() - timedelta(days=1),
    )


@pytest.fixture
def partially_fulfilled_overdue(portal):
    return DocumentRequest.objects.create(
        portal=portal,
        title="Partial Overdue",
        assignee_email="partial@example.com",
        status=REQUEST_PARTIALLY_FULFILLED,
        deadline=timezone.now() - timedelta(hours=2),
    )


# ---------------------------------------------------------------------------
# send_request_email
# ---------------------------------------------------------------------------


class TestSendRequestEmail:
    """Tests for the send_request_email task."""

    @pytest.mark.django_db
    @patch("django.core.mail.send_mail")
    def test_sends_email(self, mock_send_mail, pending_request):
        result = send_request_email(pending_request.pk)
        mock_send_mail.assert_called_once()
        assert result["request_id"] == pending_request.pk
        assert result["sent_to"] == "person@example.com"

    @pytest.mark.django_db
    @patch("django.core.mail.send_mail")
    def test_updates_sent_at(self, mock_send_mail, pending_request):
        assert pending_request.sent_at is None
        send_request_email(pending_request.pk)
        pending_request.refresh_from_db()
        assert pending_request.sent_at is not None

    @pytest.mark.django_db
    @patch("django.core.mail.send_mail")
    def test_email_contains_request_title(self, mock_send_mail, pending_request):
        send_request_email(pending_request.pk)
        call_kwargs = mock_send_mail.call_args
        subject = call_kwargs.kwargs.get("subject") or call_kwargs[0][0]
        assert "Pending Request" in subject

    @pytest.mark.django_db
    @patch("django.core.mail.send_mail")
    def test_email_contains_token_link(self, mock_send_mail, pending_request):
        send_request_email(pending_request.pk)
        call_kwargs = mock_send_mail.call_args
        body = call_kwargs.kwargs.get("message") or call_kwargs[0][1]
        assert pending_request.token in body

    @pytest.mark.django_db
    @patch("django.core.mail.send_mail")
    def test_email_sent_to_assignee(self, mock_send_mail, pending_request):
        send_request_email(pending_request.pk)
        call_kwargs = mock_send_mail.call_args
        recipients = call_kwargs.kwargs.get("recipient_list") or call_kwargs[0][3]
        assert "person@example.com" in recipients


# ---------------------------------------------------------------------------
# send_deadline_reminder
# ---------------------------------------------------------------------------


class TestSendDeadlineReminder:
    """Tests for the send_deadline_reminder task."""

    @pytest.mark.django_db
    @patch("django.core.mail.send_mail")
    def test_sends_reminder_email(self, mock_send_mail, pending_request):
        result = send_deadline_reminder(pending_request.pk)
        mock_send_mail.assert_called_once()
        assert result["request_id"] == pending_request.pk
        assert result["reminded"] == "person@example.com"

    @pytest.mark.django_db
    @patch("django.core.mail.send_mail")
    def test_updates_reminder_sent_at(self, mock_send_mail, pending_request):
        assert pending_request.reminder_sent_at is None
        send_deadline_reminder(pending_request.pk)
        pending_request.refresh_from_db()
        assert pending_request.reminder_sent_at is not None

    @pytest.mark.django_db
    @patch("django.core.mail.send_mail")
    def test_reminder_subject_contains_title(self, mock_send_mail, pending_request):
        send_deadline_reminder(pending_request.pk)
        call_kwargs = mock_send_mail.call_args
        subject = call_kwargs.kwargs.get("subject") or call_kwargs[0][0]
        assert "Reminder" in subject
        assert "Pending Request" in subject


# ---------------------------------------------------------------------------
# expire_overdue_requests
# ---------------------------------------------------------------------------


class TestExpireOverdueRequests:
    """Tests for the expire_overdue_requests task."""

    @pytest.mark.django_db
    def test_expires_overdue_pending(self, overdue_request):
        result = expire_overdue_requests()
        assert result["expired"] >= 1
        overdue_request.refresh_from_db()
        assert overdue_request.status == REQUEST_EXPIRED

    @pytest.mark.django_db
    def test_expires_overdue_partially_fulfilled(self, partially_fulfilled_overdue):
        result = expire_overdue_requests()
        assert result["expired"] >= 1
        partially_fulfilled_overdue.refresh_from_db()
        assert partially_fulfilled_overdue.status == REQUEST_EXPIRED

    @pytest.mark.django_db
    def test_does_not_expire_future_requests(self, pending_request):
        result = expire_overdue_requests()
        assert result["expired"] == 0
        pending_request.refresh_from_db()
        assert pending_request.status == REQUEST_PENDING

    @pytest.mark.django_db
    def test_does_not_expire_already_expired(self, portal):
        req = DocumentRequest.objects.create(
            portal=portal,
            title="Already Expired",
            assignee_email="a@b.com",
            status=REQUEST_EXPIRED,
            deadline=timezone.now() - timedelta(days=10),
        )
        result = expire_overdue_requests()
        assert result["expired"] == 0

    @pytest.mark.django_db
    def test_does_not_expire_requests_without_deadline(self, portal):
        req = DocumentRequest.objects.create(
            portal=portal,
            title="No Deadline",
            assignee_email="a@b.com",
            status=REQUEST_PENDING,
            deadline=None,
        )
        result = expire_overdue_requests()
        assert result["expired"] == 0
        req.refresh_from_db()
        assert req.status == REQUEST_PENDING


# ---------------------------------------------------------------------------
# check_deadline_reminders
# ---------------------------------------------------------------------------


class TestCheckDeadlineReminders:
    """Tests for the check_deadline_reminders task."""

    @pytest.mark.django_db
    @patch("portal.tasks.send_deadline_reminder.delay")
    def test_queues_reminders_for_upcoming_deadlines(
        self, mock_delay, portal, settings
    ):
        settings.PORTAL_REQUEST_REMINDER_DAYS = 3
        # Request with deadline in 2 days (within threshold) and no reminder sent
        req = DocumentRequest.objects.create(
            portal=portal,
            title="Due Soon",
            assignee_email="soon@example.com",
            status=REQUEST_PENDING,
            deadline=timezone.now() + timedelta(days=2),
            reminder_sent_at=None,
        )
        result = check_deadline_reminders()
        assert result["reminders_queued"] >= 1
        mock_delay.assert_called_with(req.pk)

    @pytest.mark.django_db
    @patch("portal.tasks.send_deadline_reminder.delay")
    def test_does_not_queue_for_far_deadlines(self, mock_delay, portal, settings):
        settings.PORTAL_REQUEST_REMINDER_DAYS = 3
        DocumentRequest.objects.create(
            portal=portal,
            title="Far Away",
            assignee_email="far@example.com",
            status=REQUEST_PENDING,
            deadline=timezone.now() + timedelta(days=30),
            reminder_sent_at=None,
        )
        result = check_deadline_reminders()
        assert result["reminders_queued"] == 0
        mock_delay.assert_not_called()

    @pytest.mark.django_db
    @patch("portal.tasks.send_deadline_reminder.delay")
    def test_does_not_queue_for_already_reminded(self, mock_delay, portal, settings):
        settings.PORTAL_REQUEST_REMINDER_DAYS = 3
        DocumentRequest.objects.create(
            portal=portal,
            title="Already Reminded",
            assignee_email="reminded@example.com",
            status=REQUEST_PENDING,
            deadline=timezone.now() + timedelta(days=1),
            reminder_sent_at=timezone.now() - timedelta(hours=1),
        )
        result = check_deadline_reminders()
        assert result["reminders_queued"] == 0
        mock_delay.assert_not_called()

    @pytest.mark.django_db
    @patch("portal.tasks.send_deadline_reminder.delay")
    def test_does_not_queue_for_past_deadlines(self, mock_delay, portal, settings):
        settings.PORTAL_REQUEST_REMINDER_DAYS = 3
        DocumentRequest.objects.create(
            portal=portal,
            title="Past Due",
            assignee_email="past@example.com",
            status=REQUEST_PENDING,
            deadline=timezone.now() - timedelta(days=1),
            reminder_sent_at=None,
        )
        result = check_deadline_reminders()
        assert result["reminders_queued"] == 0
        mock_delay.assert_not_called()

    @pytest.mark.django_db
    @patch("portal.tasks.send_deadline_reminder.delay")
    def test_does_not_queue_for_non_pending_status(
        self, mock_delay, portal, settings
    ):
        settings.PORTAL_REQUEST_REMINDER_DAYS = 3
        DocumentRequest.objects.create(
            portal=portal,
            title="Already Fulfilled",
            assignee_email="done@example.com",
            status=REQUEST_PARTIALLY_FULFILLED,
            deadline=timezone.now() + timedelta(days=1),
            reminder_sent_at=None,
        )
        result = check_deadline_reminders()
        assert result["reminders_queued"] == 0
        mock_delay.assert_not_called()

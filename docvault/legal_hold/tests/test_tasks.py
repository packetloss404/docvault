"""Tests for legal_hold Celery tasks."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from legal_hold.constants import ACTIVE, SEARCH_QUERY, SPECIFIC_DOCUMENTS
from legal_hold.models import (
    LegalHold,
    LegalHoldCriteria,
    LegalHoldCustodian,
    LegalHoldDocument,
)
from legal_hold.tasks import notify_custodians, reevaluate_holds

User = get_user_model()

PATCH_SEND_MAIL = "django.core.mail.send_mail"


@pytest.fixture
def user(db):
    return User.objects.create_user(
        "testuser", "test@example.com", "password"
    )


@pytest.fixture
def user_with_email(db):
    return User.objects.create_user(
        "emailuser", "emailuser@example.com", "password"
    )


@pytest.fixture
def hold(user):
    return LegalHold.objects.create(
        name="Task Hold",
        status=ACTIVE,
        created_by=user,
    )


@pytest.fixture
def document(user):
    from documents.models import Document

    return Document.objects.create(title="Task Doc", owner=user)


# ===========================================================================
# notify_custodians
# ===========================================================================


@pytest.mark.django_db
def test_notify_custodians_sends_email(hold, user_with_email):
    custodian = LegalHoldCustodian.objects.create(
        hold=hold, user=user_with_email
    )
    assert custodian.notified_at is None

    with patch(PATCH_SEND_MAIL) as mock_send:
        notify_custodians(hold.pk)

    mock_send.assert_called_once()
    call_args = mock_send.call_args
    # send_mail may be called with positional or keyword args
    subject = call_args.kwargs.get("subject") or call_args.args[0]
    assert "Legal Hold Notice" in subject

    custodian.refresh_from_db()
    assert custodian.notified_at is not None


@pytest.mark.django_db
def test_notify_custodians_skips_already_notified(hold, user_with_email):
    from django.utils import timezone

    LegalHoldCustodian.objects.create(
        hold=hold, user=user_with_email, notified_at=timezone.now()
    )

    with patch(PATCH_SEND_MAIL) as mock_send:
        notify_custodians(hold.pk)

    mock_send.assert_not_called()


@pytest.mark.django_db
def test_notify_custodians_skips_no_email(hold, user):
    """Custodian users without email addresses should be skipped."""
    user.email = ""
    user.save()
    LegalHoldCustodian.objects.create(hold=hold, user=user)

    with patch(PATCH_SEND_MAIL) as mock_send:
        notify_custodians(hold.pk)

    mock_send.assert_not_called()


@pytest.mark.django_db
def test_notify_custodians_nonexistent_hold():
    """Should handle non-existent hold gracefully without raising."""
    notify_custodians(99999)  # Should not raise


# ===========================================================================
# reevaluate_holds
# ===========================================================================


@pytest.mark.django_db
def test_reevaluate_holds_refreshes_search_query_holds(hold, user, document):
    """Active holds with SEARCH_QUERY criteria should be re-evaluated."""
    LegalHoldCriteria.objects.create(
        hold=hold,
        criteria_type=SEARCH_QUERY,
        value={"query": "Task"},
    )
    # Document content matches the query
    document.content = "This is a Task document"
    document.save()

    # reevaluate_holds imports refresh_hold from legal_hold.engine inside
    # the function body, so we need to call the real function and just
    # verify the end result rather than mocking the import.
    reevaluate_holds()

    # refresh_hold should have captured the matching document
    from legal_hold.models import LegalHoldDocument

    assert LegalHoldDocument.objects.filter(hold=hold, document=document).exists()

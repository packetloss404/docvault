"""Tests for physical_records Celery tasks."""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from physical_records.constants import CHECKED_OUT, GOOD, OVERDUE, SHELF
from physical_records.models import ChargeOut, PhysicalLocation, PhysicalRecord
from physical_records.tasks import check_overdue_charge_outs

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user("testuser", "test@example.com", "password")


@pytest.fixture
def document(user):
    from documents.models import Document

    return Document.objects.create(title="Test Doc", owner=user)


@pytest.fixture
def document2(user):
    from documents.models import Document

    return Document.objects.create(title="Test Doc 2", owner=user)


@pytest.fixture
def location():
    return PhysicalLocation.objects.create(
        name="Shelf A", location_type=SHELF
    )


@pytest.fixture
def physical_record(document, location, user):
    return PhysicalRecord.objects.create(
        document=document,
        location=location,
        condition=GOOD,
        created_by=user,
    )


@pytest.fixture
def physical_record2(document2, location, user):
    return PhysicalRecord.objects.create(
        document=document2,
        location=location,
        condition=GOOD,
        created_by=user,
    )


@pytest.mark.django_db
def test_check_overdue_marks_past_due(user, physical_record):
    """Charge-outs past expected_return should be marked OVERDUE."""
    co = ChargeOut.objects.create(
        physical_record=physical_record,
        user=user,
        expected_return=timezone.now() - timezone.timedelta(days=1),
        status=CHECKED_OUT,
    )

    result = check_overdue_charge_outs()
    co.refresh_from_db()

    assert co.status == OVERDUE
    assert result["overdue_count"] == 1


@pytest.mark.django_db
def test_check_overdue_skips_not_yet_due(user, physical_record):
    """Charge-outs not yet due should not be marked OVERDUE."""
    co = ChargeOut.objects.create(
        physical_record=physical_record,
        user=user,
        expected_return=timezone.now() + timezone.timedelta(days=7),
        status=CHECKED_OUT,
    )

    result = check_overdue_charge_outs()
    co.refresh_from_db()

    assert co.status == CHECKED_OUT
    assert result["overdue_count"] == 0


@pytest.mark.django_db
def test_check_overdue_skips_already_returned(user, physical_record):
    """Returned charge-outs should not be changed."""
    from physical_records.constants import RETURNED

    co = ChargeOut.objects.create(
        physical_record=physical_record,
        user=user,
        expected_return=timezone.now() - timezone.timedelta(days=1),
        status=RETURNED,
        returned_at=timezone.now(),
    )

    result = check_overdue_charge_outs()
    co.refresh_from_db()

    assert co.status == RETURNED
    assert result["overdue_count"] == 0


@pytest.mark.django_db
def test_check_overdue_multiple(user, physical_record, physical_record2):
    """Multiple overdue charge-outs should all be updated."""
    ChargeOut.objects.create(
        physical_record=physical_record,
        user=user,
        expected_return=timezone.now() - timezone.timedelta(days=2),
        status=CHECKED_OUT,
    )
    ChargeOut.objects.create(
        physical_record=physical_record2,
        user=user,
        expected_return=timezone.now() - timezone.timedelta(days=1),
        status=CHECKED_OUT,
    )

    result = check_overdue_charge_outs()
    assert result["overdue_count"] == 2


@pytest.mark.django_db
def test_check_overdue_no_charge_outs():
    """No charge-outs should return count 0."""
    result = check_overdue_charge_outs()
    assert result["overdue_count"] == 0

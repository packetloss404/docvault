"""Tests for physical_records models."""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone

from physical_records.constants import (
    BOX,
    BUILDING,
    CABINET,
    CHECKED_OUT,
    DAMAGED,
    FAIR,
    GOOD,
    INCINERATION,
    OVERDUE,
    POOR,
    RETURNED,
    ROOM,
    SHELF,
    SHREDDING,
)
from physical_records.models import (
    ChargeOut,
    DestructionCertificate,
    PhysicalLocation,
    PhysicalRecord,
)

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
def building():
    return PhysicalLocation.objects.create(
        name="Main Building", location_type=BUILDING
    )


@pytest.fixture
def room(building):
    return PhysicalLocation.objects.create(
        name="Room 101", location_type=ROOM, parent=building
    )


@pytest.fixture
def shelf(room):
    return PhysicalLocation.objects.create(
        name="Shelf A", location_type=SHELF, parent=room
    )


@pytest.fixture
def physical_record(document, shelf, user):
    return PhysicalRecord.objects.create(
        document=document,
        location=shelf,
        barcode="REC-001",
        condition=GOOD,
        created_by=user,
    )


# ===========================================================================
# PhysicalLocation
# ===========================================================================


@pytest.mark.django_db
def test_physical_location_creation(building):
    assert building.name == "Main Building"
    assert building.location_type == BUILDING
    assert building.parent is None
    assert building.is_active is True
    assert building.current_count == 0


@pytest.mark.django_db
def test_physical_location_hierarchy(building, room, shelf):
    """PhysicalLocation supports MPTT parent-child hierarchy."""
    assert room.parent == building
    assert shelf.parent == room
    # MPTT methods
    assert building.is_root_node()
    assert not room.is_root_node()
    children = building.get_children()
    assert room in children


@pytest.mark.django_db
def test_physical_location_str(building):
    assert str(building) == "Building: Main Building"


@pytest.mark.django_db
def test_physical_location_all_types():
    for loc_type, display in [
        (BUILDING, "Building"),
        (ROOM, "Room"),
        (CABINET, "Cabinet"),
        (SHELF, "Shelf"),
        (BOX, "Box"),
    ]:
        loc = PhysicalLocation.objects.create(
            name=f"Test {display}", location_type=loc_type
        )
        assert loc.location_type == loc_type


@pytest.mark.django_db
def test_physical_location_barcode_unique():
    PhysicalLocation.objects.create(
        name="Loc A", location_type=ROOM, barcode="LOC-001"
    )
    with pytest.raises(IntegrityError):
        PhysicalLocation.objects.create(
            name="Loc B", location_type=ROOM, barcode="LOC-001"
        )


@pytest.mark.django_db
def test_physical_location_capacity(building):
    building.capacity = 100
    building.save()
    building.refresh_from_db()
    assert building.capacity == 100


# ===========================================================================
# PhysicalRecord
# ===========================================================================


@pytest.mark.django_db
def test_physical_record_creation(physical_record, document, shelf):
    assert physical_record.document == document
    assert physical_record.location == shelf
    assert physical_record.barcode == "REC-001"
    assert physical_record.condition == GOOD
    assert physical_record.created_at is not None


@pytest.mark.django_db
def test_physical_record_onetoone_with_document(document, user):
    """Only one PhysicalRecord can exist per Document."""
    PhysicalRecord.objects.create(
        document=document, barcode="REC-A", created_by=user
    )
    with pytest.raises(IntegrityError):
        PhysicalRecord.objects.create(
            document=document, barcode="REC-B", created_by=user
        )


@pytest.mark.django_db
def test_physical_record_condition_choices(document2, user):
    for cond in [GOOD, FAIR, POOR, DAMAGED]:
        record = PhysicalRecord.objects.create(
            document=document2, condition=cond, created_by=user
        )
        assert record.condition == cond
        record.delete()


@pytest.mark.django_db
def test_physical_record_str(physical_record):
    assert "Physical Record" in str(physical_record)
    assert "Test Doc" in str(physical_record)


@pytest.mark.django_db
def test_physical_record_cascade_delete_document(physical_record, document):
    """Deleting the document cascades to the physical record."""
    assert PhysicalRecord.objects.count() == 1
    document.hard_delete()
    assert PhysicalRecord.objects.count() == 0


# ===========================================================================
# ChargeOut
# ===========================================================================


@pytest.mark.django_db
def test_charge_out_creation(physical_record, user):
    now = timezone.now()
    expected_return = now + timezone.timedelta(days=7)
    co = ChargeOut.objects.create(
        physical_record=physical_record,
        user=user,
        expected_return=expected_return,
    )
    assert co.physical_record == physical_record
    assert co.user == user
    assert co.status == CHECKED_OUT
    assert co.returned_at is None
    assert co.checked_out_at is not None


@pytest.mark.django_db
def test_charge_out_status_choices(physical_record, user):
    now = timezone.now()
    for status_val in [CHECKED_OUT, RETURNED, OVERDUE]:
        co = ChargeOut.objects.create(
            physical_record=physical_record,
            user=user,
            expected_return=now + timezone.timedelta(days=1),
            status=status_val,
        )
        assert co.status == status_val


@pytest.mark.django_db
def test_charge_out_str(physical_record, user):
    co = ChargeOut.objects.create(
        physical_record=physical_record,
        user=user,
        expected_return=timezone.now() + timezone.timedelta(days=1),
    )
    assert "ChargeOut" in str(co)


@pytest.mark.django_db
def test_charge_out_cascade_delete(physical_record, user):
    ChargeOut.objects.create(
        physical_record=physical_record,
        user=user,
        expected_return=timezone.now() + timezone.timedelta(days=1),
    )
    assert ChargeOut.objects.count() == 1
    physical_record.delete()
    assert ChargeOut.objects.count() == 0


# ===========================================================================
# DestructionCertificate
# ===========================================================================


@pytest.mark.django_db
def test_destruction_certificate_creation(physical_record, user):
    cert = DestructionCertificate.objects.create(
        physical_record=physical_record,
        destroyed_at=timezone.now(),
        destroyed_by=user,
        method=SHREDDING,
        witness="John Smith",
        notes="Destroyed per policy",
    )
    assert cert.method == SHREDDING
    assert cert.witness == "John Smith"
    assert cert.notes == "Destroyed per policy"
    assert cert.destroyed_by == user


@pytest.mark.django_db
def test_destruction_certificate_str(physical_record, user):
    cert = DestructionCertificate.objects.create(
        physical_record=physical_record,
        destroyed_at=timezone.now(),
        destroyed_by=user,
        method=INCINERATION,
    )
    assert "Destruction Certificate" in str(cert)


@pytest.mark.django_db
def test_destruction_certificate_cascade_delete(physical_record, user):
    DestructionCertificate.objects.create(
        physical_record=physical_record,
        destroyed_at=timezone.now(),
        destroyed_by=user,
        method=SHREDDING,
    )
    assert DestructionCertificate.objects.count() == 1
    physical_record.delete()
    assert DestructionCertificate.objects.count() == 0

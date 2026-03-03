"""Tests for legal_hold models."""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from legal_hold.constants import (
    ACTIVE,
    CABINET,
    CUSTODIAN,
    DATE_RANGE,
    DOCUMENT_TYPE,
    DRAFT,
    RELEASED,
    SEARCH_QUERY,
    SPECIFIC_DOCUMENTS,
    TAG,
)
from legal_hold.models import (
    LegalHold,
    LegalHoldCriteria,
    LegalHoldCustodian,
    LegalHoldDocument,
)

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user("testuser", "test@example.com", "password")


@pytest.fixture
def user2(db):
    return User.objects.create_user("testuser2", "test2@example.com", "password")


@pytest.fixture
def document(user):
    from documents.models import Document

    return Document.objects.create(title="Test Doc", owner=user)


@pytest.fixture
def document2(user):
    from documents.models import Document

    return Document.objects.create(title="Test Doc 2", owner=user)


@pytest.fixture
def hold(user):
    return LegalHold.objects.create(
        name="Test Hold",
        matter_number="CASE-001",
        description="Test hold description",
        created_by=user,
    )


# ===========================================================================
# LegalHold Creation and Defaults
# ===========================================================================


@pytest.mark.django_db
def test_legal_hold_creation(user):
    hold = LegalHold.objects.create(name="My Hold", created_by=user)
    assert hold.name == "My Hold"
    assert hold.status == DRAFT
    assert hold.matter_number == ""
    assert hold.description == ""
    assert hold.activated_at is None
    assert hold.released_at is None
    assert hold.released_by is None
    assert hold.release_reason == ""
    assert hold.created_at is not None
    assert hold.updated_at is not None


@pytest.mark.django_db
def test_legal_hold_str(hold):
    assert str(hold) == "Test Hold (draft)"


@pytest.mark.django_db
def test_legal_hold_status_choices(user):
    for status_val, _ in [(DRAFT, "Draft"), (ACTIVE, "Active"), (RELEASED, "Released")]:
        hold = LegalHold.objects.create(
            name=f"Hold {status_val}", status=status_val, created_by=user
        )
        assert hold.status == status_val


@pytest.mark.django_db
def test_legal_hold_default_status(user):
    hold = LegalHold.objects.create(name="Draft Hold", created_by=user)
    assert hold.status == DRAFT


@pytest.mark.django_db
def test_legal_hold_ordering(user):
    """Holds are ordered by -created_at by default."""
    h1 = LegalHold.objects.create(name="First", created_by=user)
    h2 = LegalHold.objects.create(name="Second", created_by=user)
    holds = list(LegalHold.objects.all())
    # Most recently created first
    assert holds[0].pk == h2.pk
    assert holds[1].pk == h1.pk


@pytest.mark.django_db
def test_legal_hold_with_matter_number(user):
    hold = LegalHold.objects.create(
        name="Matter Hold", matter_number="MATTER-2024-001", created_by=user
    )
    assert hold.matter_number == "MATTER-2024-001"


# ===========================================================================
# LegalHoldCriteria
# ===========================================================================


@pytest.mark.django_db
def test_legal_hold_criteria_creation(hold):
    criteria = LegalHoldCriteria.objects.create(
        hold=hold,
        criteria_type=CUSTODIAN,
        value={"user_ids": [1, 2]},
    )
    assert criteria.criteria_type == CUSTODIAN
    assert criteria.value == {"user_ids": [1, 2]}
    assert criteria.hold == hold


@pytest.mark.django_db
def test_legal_hold_criteria_all_types(hold):
    for ct, _ in [
        (CUSTODIAN, "Custodian"),
        (DATE_RANGE, "Date Range"),
        (TAG, "Tag"),
        (DOCUMENT_TYPE, "Document Type"),
        (SEARCH_QUERY, "Search Query"),
        (CABINET, "Cabinet"),
        (SPECIFIC_DOCUMENTS, "Specific Documents"),
    ]:
        c = LegalHoldCriteria.objects.create(
            hold=hold, criteria_type=ct, value={}
        )
        assert c.criteria_type == ct


@pytest.mark.django_db
def test_legal_hold_criteria_str(hold):
    criteria = LegalHoldCriteria.objects.create(
        hold=hold, criteria_type=TAG, value={"tag_ids": [1]}
    )
    assert "Test Hold" in str(criteria)
    assert "Tag" in str(criteria)


@pytest.mark.django_db
def test_legal_hold_criteria_cascade_delete(hold):
    LegalHoldCriteria.objects.create(
        hold=hold, criteria_type=TAG, value={"tag_ids": [1]}
    )
    assert LegalHoldCriteria.objects.count() == 1
    hold.delete()
    assert LegalHoldCriteria.objects.count() == 0


@pytest.mark.django_db
def test_legal_hold_criteria_ordering(hold):
    c1 = LegalHoldCriteria.objects.create(
        hold=hold, criteria_type=TAG, value={}
    )
    c2 = LegalHoldCriteria.objects.create(
        hold=hold, criteria_type=CUSTODIAN, value={}
    )
    criteria = list(hold.criteria.all())
    assert criteria[0].pk == c1.pk
    assert criteria[1].pk == c2.pk


# ===========================================================================
# LegalHoldCustodian
# ===========================================================================


@pytest.mark.django_db
def test_legal_hold_custodian_creation(hold, user):
    custodian = LegalHoldCustodian.objects.create(hold=hold, user=user)
    assert custodian.hold == hold
    assert custodian.user == user
    assert custodian.notified_at is None
    assert custodian.acknowledged is False
    assert custodian.acknowledged_at is None
    assert custodian.notes == ""


@pytest.mark.django_db
def test_legal_hold_custodian_unique_constraint(hold, user):
    LegalHoldCustodian.objects.create(hold=hold, user=user)
    with pytest.raises(IntegrityError):
        LegalHoldCustodian.objects.create(hold=hold, user=user)


@pytest.mark.django_db
def test_legal_hold_custodian_different_holds(user):
    h1 = LegalHold.objects.create(name="Hold 1", created_by=user)
    h2 = LegalHold.objects.create(name="Hold 2", created_by=user)
    c1 = LegalHoldCustodian.objects.create(hold=h1, user=user)
    c2 = LegalHoldCustodian.objects.create(hold=h2, user=user)
    assert c1.pk != c2.pk


@pytest.mark.django_db
def test_legal_hold_custodian_str(hold, user):
    custodian = LegalHoldCustodian.objects.create(hold=hold, user=user)
    assert "Test Hold" in str(custodian)
    assert "testuser" in str(custodian)


@pytest.mark.django_db
def test_legal_hold_custodian_cascade_delete(hold, user):
    LegalHoldCustodian.objects.create(hold=hold, user=user)
    assert LegalHoldCustodian.objects.count() == 1
    hold.delete()
    assert LegalHoldCustodian.objects.count() == 0


# ===========================================================================
# LegalHoldDocument
# ===========================================================================


@pytest.mark.django_db
def test_legal_hold_document_creation(hold, document):
    lhd = LegalHoldDocument.objects.create(hold=hold, document=document)
    assert lhd.hold == hold
    assert lhd.document == document
    assert lhd.held_at is not None
    assert lhd.released_at is None


@pytest.mark.django_db
def test_legal_hold_document_unique_constraint(hold, document):
    LegalHoldDocument.objects.create(hold=hold, document=document)
    with pytest.raises(IntegrityError):
        LegalHoldDocument.objects.create(hold=hold, document=document)


@pytest.mark.django_db
def test_legal_hold_document_str(hold, document):
    lhd = LegalHoldDocument.objects.create(hold=hold, document=document)
    assert "Test Hold" in str(lhd)


@pytest.mark.django_db
def test_legal_hold_document_cascade_delete_hold(hold, document):
    LegalHoldDocument.objects.create(hold=hold, document=document)
    assert LegalHoldDocument.objects.count() == 1
    hold.delete()
    assert LegalHoldDocument.objects.count() == 0


@pytest.mark.django_db
def test_legal_hold_document_cascade_delete_document(hold, document):
    LegalHoldDocument.objects.create(hold=hold, document=document)
    assert LegalHoldDocument.objects.count() == 1
    document.hard_delete()
    assert LegalHoldDocument.objects.count() == 0

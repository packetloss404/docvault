"""Tests for the legal_hold engine module."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

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
from legal_hold.engine import activate_hold, evaluate_criteria, refresh_hold, release_hold
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
def hold(user):
    return LegalHold.objects.create(
        name="Test Hold",
        matter_number="CASE-001",
        created_by=user,
    )


@pytest.fixture
def tag(user):
    from organization.models import Tag

    return Tag.objects.create(name="Important", slug="important", owner=user)


@pytest.fixture
def cabinet(user):
    from organization.models import Cabinet

    return Cabinet.objects.create(name="Legal Docs", slug="legal-docs", owner=user)


@pytest.fixture
def document_type(user):
    from documents.models import DocumentType

    return DocumentType.objects.create(name="Invoice", slug="invoice", owner=user)


@pytest.fixture
def document(user):
    from documents.models import Document

    return Document.objects.create(title="Test Doc", owner=user)


@pytest.fixture
def document2(user):
    from documents.models import Document

    return Document.objects.create(title="Test Doc 2", owner=user)


@pytest.fixture
def document3(user2):
    from documents.models import Document

    return Document.objects.create(title="Test Doc 3", owner=user2)


# Patch send_mail globally since CELERY_TASK_ALWAYS_EAGER=True causes
# notify_custodians to run synchronously within activate_hold.
PATCH_SEND_MAIL = "django.core.mail.send_mail"


# ===========================================================================
# evaluate_criteria tests
# ===========================================================================


@pytest.mark.django_db
def test_evaluate_criteria_no_criteria(hold):
    result = evaluate_criteria(hold)
    assert result == []


@pytest.mark.django_db
def test_evaluate_criteria_custodian(hold, user, document, document3):
    """CUSTODIAN criteria should match docs owned by or created by those user_ids."""
    LegalHoldCriteria.objects.create(
        hold=hold, criteria_type=CUSTODIAN, value={"user_ids": [user.pk]}
    )
    result = evaluate_criteria(hold)
    assert document.pk in result
    assert document3.pk not in result


@pytest.mark.django_db
def test_evaluate_criteria_date_range(hold, user):
    from datetime import date

    from documents.models import Document

    d1 = Document.objects.create(title="Old", owner=user, created=date(2020, 1, 1))
    d2 = Document.objects.create(title="New", owner=user, created=date(2024, 6, 15))

    LegalHoldCriteria.objects.create(
        hold=hold,
        criteria_type=DATE_RANGE,
        value={"start": "2020-01-01", "end": "2020-12-31"},
    )
    result = evaluate_criteria(hold)
    assert d1.pk in result
    assert d2.pk not in result


@pytest.mark.django_db
def test_evaluate_criteria_tag(hold, user, tag):
    from documents.models import Document

    d1 = Document.objects.create(title="Tagged", owner=user)
    d1.tags.add(tag)
    d2 = Document.objects.create(title="Untagged", owner=user)

    LegalHoldCriteria.objects.create(
        hold=hold, criteria_type=TAG, value={"tag_ids": [tag.pk]}
    )
    result = evaluate_criteria(hold)
    assert d1.pk in result
    assert d2.pk not in result


@pytest.mark.django_db
def test_evaluate_criteria_document_type(hold, user, document_type):
    from documents.models import Document

    d1 = Document.objects.create(title="Typed", owner=user, document_type=document_type)
    d2 = Document.objects.create(title="Untyped", owner=user)

    LegalHoldCriteria.objects.create(
        hold=hold,
        criteria_type=DOCUMENT_TYPE,
        value={"type_ids": [document_type.pk]},
    )
    result = evaluate_criteria(hold)
    assert d1.pk in result
    assert d2.pk not in result


@pytest.mark.django_db
def test_evaluate_criteria_search_query(hold, user):
    from documents.models import Document

    d1 = Document.objects.create(
        title="Contract", owner=user, content="This is a confidential contract."
    )
    d2 = Document.objects.create(
        title="Invoice", owner=user, content="Standard invoice for services."
    )

    LegalHoldCriteria.objects.create(
        hold=hold, criteria_type=SEARCH_QUERY, value={"query": "confidential"}
    )
    result = evaluate_criteria(hold)
    assert d1.pk in result
    assert d2.pk not in result


@pytest.mark.django_db
def test_evaluate_criteria_cabinet(hold, user, cabinet):
    from documents.models import Document

    d1 = Document.objects.create(title="In cabinet", owner=user, cabinet=cabinet)
    d2 = Document.objects.create(title="No cabinet", owner=user)

    LegalHoldCriteria.objects.create(
        hold=hold, criteria_type=CABINET, value={"cabinet_ids": [cabinet.pk]}
    )
    result = evaluate_criteria(hold)
    assert d1.pk in result
    assert d2.pk not in result


@pytest.mark.django_db
def test_evaluate_criteria_specific_documents(hold, document, document2):
    LegalHoldCriteria.objects.create(
        hold=hold,
        criteria_type=SPECIFIC_DOCUMENTS,
        value={"document_ids": [document.pk]},
    )
    result = evaluate_criteria(hold)
    assert document.pk in result
    assert document2.pk not in result


@pytest.mark.django_db
def test_evaluate_criteria_multiple_and_logic(hold, user, tag):
    """Multiple criteria are combined with AND logic."""
    from documents.models import Document

    d1 = Document.objects.create(
        title="Match both", owner=user, content="confidential data"
    )
    d1.tags.add(tag)
    d2 = Document.objects.create(
        title="Tag only", owner=user, content="public data"
    )
    d2.tags.add(tag)
    d3 = Document.objects.create(
        title="Query only", owner=user, content="confidential data"
    )

    LegalHoldCriteria.objects.create(
        hold=hold, criteria_type=TAG, value={"tag_ids": [tag.pk]}
    )
    LegalHoldCriteria.objects.create(
        hold=hold, criteria_type=SEARCH_QUERY, value={"query": "confidential"}
    )
    result = evaluate_criteria(hold)
    assert d1.pk in result
    assert d2.pk not in result
    assert d3.pk not in result


@pytest.mark.django_db
def test_evaluate_criteria_empty_search_query(hold, document):
    """An empty search query should still return results (no filter applied)."""
    LegalHoldCriteria.objects.create(
        hold=hold, criteria_type=SEARCH_QUERY, value={"query": ""}
    )
    result = evaluate_criteria(hold)
    assert document.pk in result


# ===========================================================================
# activate_hold tests
# ===========================================================================


@pytest.mark.django_db
def test_activate_hold_creates_legal_hold_documents(hold, document, document2):
    LegalHoldCriteria.objects.create(
        hold=hold,
        criteria_type=SPECIFIC_DOCUMENTS,
        value={"document_ids": [document.pk, document2.pk]},
    )
    with patch(PATCH_SEND_MAIL):
        count = activate_hold(hold)
    assert count == 2
    assert LegalHoldDocument.objects.filter(hold=hold).count() == 2


@pytest.mark.django_db
def test_activate_hold_sets_is_held(hold, document):
    LegalHoldCriteria.objects.create(
        hold=hold,
        criteria_type=SPECIFIC_DOCUMENTS,
        value={"document_ids": [document.pk]},
    )
    with patch(PATCH_SEND_MAIL):
        activate_hold(hold)

    document.refresh_from_db()
    assert document.is_held is True


@pytest.mark.django_db
def test_activate_hold_changes_status_to_active(hold, document):
    LegalHoldCriteria.objects.create(
        hold=hold,
        criteria_type=SPECIFIC_DOCUMENTS,
        value={"document_ids": [document.pk]},
    )
    with patch(PATCH_SEND_MAIL):
        activate_hold(hold)

    hold.refresh_from_db()
    assert hold.status == ACTIVE
    assert hold.activated_at is not None


@pytest.mark.django_db
def test_activate_hold_triggers_notification(hold, user, document):
    """Activating a hold should trigger custodian notification."""
    LegalHoldCustodian.objects.create(hold=hold, user=user)
    LegalHoldCriteria.objects.create(
        hold=hold,
        criteria_type=SPECIFIC_DOCUMENTS,
        value={"document_ids": [document.pk]},
    )
    with patch(PATCH_SEND_MAIL) as mock_send:
        activate_hold(hold)
    # Since CELERY_TASK_ALWAYS_EAGER=True, send_mail should be called
    mock_send.assert_called_once()


@pytest.mark.django_db
def test_activate_hold_no_matching_documents(hold):
    """Activating a hold with no criteria captures 0 documents."""
    with patch(PATCH_SEND_MAIL):
        count = activate_hold(hold)
    assert count == 0
    hold.refresh_from_db()
    assert hold.status == ACTIVE


@pytest.mark.django_db
def test_activate_hold_skips_duplicates(hold, document):
    """If a document is already held, it is not duplicated."""
    LegalHoldCriteria.objects.create(
        hold=hold,
        criteria_type=SPECIFIC_DOCUMENTS,
        value={"document_ids": [document.pk]},
    )
    # Pre-create the junction record
    LegalHoldDocument.objects.create(hold=hold, document=document)

    with patch(PATCH_SEND_MAIL):
        count = activate_hold(hold)

    # Count still includes the document, but no duplicate created
    assert count == 1
    assert LegalHoldDocument.objects.filter(hold=hold).count() == 1


# ===========================================================================
# release_hold tests
# ===========================================================================


@pytest.mark.django_db
def test_release_hold_changes_status(hold, user, document):
    LegalHoldCriteria.objects.create(
        hold=hold,
        criteria_type=SPECIFIC_DOCUMENTS,
        value={"document_ids": [document.pk]},
    )
    with patch(PATCH_SEND_MAIL):
        activate_hold(hold)

    release_hold(hold, user, reason="Case closed")
    hold.refresh_from_db()
    assert hold.status == RELEASED
    assert hold.released_at is not None
    assert hold.released_by == user
    assert hold.release_reason == "Case closed"


@pytest.mark.django_db
def test_release_hold_clears_is_held(hold, user, document):
    LegalHoldCriteria.objects.create(
        hold=hold,
        criteria_type=SPECIFIC_DOCUMENTS,
        value={"document_ids": [document.pk]},
    )
    with patch(PATCH_SEND_MAIL):
        activate_hold(hold)

    release_hold(hold, user)
    document.refresh_from_db()
    assert document.is_held is False


@pytest.mark.django_db
def test_release_hold_keeps_is_held_if_other_active_hold(hold, user, document):
    """If another active hold covers the same document, is_held stays True."""
    hold2 = LegalHold.objects.create(name="Hold 2", created_by=user)

    LegalHoldCriteria.objects.create(
        hold=hold,
        criteria_type=SPECIFIC_DOCUMENTS,
        value={"document_ids": [document.pk]},
    )
    LegalHoldCriteria.objects.create(
        hold=hold2,
        criteria_type=SPECIFIC_DOCUMENTS,
        value={"document_ids": [document.pk]},
    )

    with patch(PATCH_SEND_MAIL):
        activate_hold(hold)
        activate_hold(hold2)

    # Release only the first hold
    release_hold(hold, user)
    document.refresh_from_db()
    assert document.is_held is True  # Still held by hold2


@pytest.mark.django_db
def test_release_hold_sets_released_at_on_documents(hold, user, document):
    LegalHoldCriteria.objects.create(
        hold=hold,
        criteria_type=SPECIFIC_DOCUMENTS,
        value={"document_ids": [document.pk]},
    )
    with patch(PATCH_SEND_MAIL):
        activate_hold(hold)

    release_hold(hold, user)
    lhd = LegalHoldDocument.objects.get(hold=hold, document=document)
    assert lhd.released_at is not None


# ===========================================================================
# refresh_hold tests
# ===========================================================================


@pytest.mark.django_db
def test_refresh_hold_adds_new_matches(hold, user, document, document2):
    """Refreshing an active hold should capture newly matching documents."""
    LegalHoldCriteria.objects.create(
        hold=hold,
        criteria_type=SPECIFIC_DOCUMENTS,
        value={"document_ids": [document.pk]},
    )

    with patch(PATCH_SEND_MAIL):
        activate_hold(hold)

    assert LegalHoldDocument.objects.filter(hold=hold).count() == 1

    # Update criteria to include second document
    hold.criteria.all().update(
        value={"document_ids": [document.pk, document2.pk]}
    )

    new_count = refresh_hold(hold)
    assert new_count == 1
    assert LegalHoldDocument.objects.filter(hold=hold).count() == 2

    document2.refresh_from_db()
    assert document2.is_held is True


@pytest.mark.django_db
def test_refresh_hold_no_new_matches(hold, document):
    """Refreshing when no new documents match returns 0."""
    LegalHoldCriteria.objects.create(
        hold=hold,
        criteria_type=SPECIFIC_DOCUMENTS,
        value={"document_ids": [document.pk]},
    )

    with patch(PATCH_SEND_MAIL):
        activate_hold(hold)

    new_count = refresh_hold(hold)
    assert new_count == 0

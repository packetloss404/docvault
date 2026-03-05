"""Tests for legal_hold API views."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from legal_hold.constants import ACTIVE, DRAFT
from legal_hold.models import (
    LegalHold,
    LegalHoldCriteria,
    LegalHoldCustodian,
    LegalHoldDocument,
)

User = get_user_model()

HOLDS_URL = "/api/v1/legal-holds/"
PATCH_SEND_MAIL = "django.core.mail.send_mail"


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user("testuser", "test@example.com", "password")


@pytest.fixture
def staff_user(db):
    u = User.objects.create_user("staffuser", "staff@example.com", "password")
    u.is_staff = True
    u.save()
    return u


@pytest.fixture
def non_staff_user(db):
    return User.objects.create_user("regular", "regular@example.com", "password")


@pytest.fixture
def document(user):
    from documents.models import Document

    return Document.objects.create(title="Test Doc", owner=user)


@pytest.fixture
def document2(user):
    from documents.models import Document

    return Document.objects.create(title="Test Doc 2", owner=user)


@pytest.fixture
def hold(staff_user):
    return LegalHold.objects.create(
        name="Test Hold",
        matter_number="CASE-001",
        description="Test hold",
        created_by=staff_user,
    )


@pytest.fixture
def active_hold(staff_user, document):
    h = LegalHold.objects.create(
        name="Active Hold", status=ACTIVE, created_by=staff_user
    )
    LegalHoldDocument.objects.create(hold=h, document=document)
    return h


# ===========================================================================
# List
# ===========================================================================


class TestLegalHoldList:
    @pytest.mark.django_db
    def test_list_holds(self, client, staff_user, hold):
        client.force_authenticate(user=staff_user)
        response = client.get(HOLDS_URL)
        assert response.status_code == 200
        data = response.data.get("results", response.data)
        assert len(data) >= 1
        names = [h["name"] for h in data]
        assert "Test Hold" in names

    @pytest.mark.django_db
    def test_list_holds_unauthenticated(self, client):
        response = client.get(HOLDS_URL)
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    def test_list_holds_non_staff_forbidden(self, client, non_staff_user, hold):
        client.force_authenticate(user=non_staff_user)
        response = client.get(HOLDS_URL)
        assert response.status_code == 403


# ===========================================================================
# Create
# ===========================================================================


class TestLegalHoldCreate:
    @pytest.mark.django_db
    def test_create_hold(self, client, staff_user):
        client.force_authenticate(user=staff_user)
        data = {
            "name": "New Hold",
            "matter_number": "CASE-002",
            "description": "A new legal hold",
        }
        response = client.post(HOLDS_URL, data, format="json")
        assert response.status_code == 201
        assert response.data["name"] == "New Hold"

    @pytest.mark.django_db
    def test_create_hold_with_criteria(self, client, staff_user):
        client.force_authenticate(user=staff_user)
        data = {
            "name": "Hold With Criteria",
            "criteria": [
                {"criteria_type": "tag", "value": {"tag_ids": [1]}},
                {"criteria_type": "search_query", "value": {"query": "confidential"}},
            ],
        }
        response = client.post(HOLDS_URL, data, format="json")
        assert response.status_code == 201
        hold = LegalHold.objects.get(pk=response.data["id"])
        assert hold.criteria.count() == 2

    @pytest.mark.django_db
    def test_create_hold_non_staff_forbidden(self, client, non_staff_user):
        client.force_authenticate(user=non_staff_user)
        data = {"name": "Forbidden Hold"}
        response = client.post(HOLDS_URL, data, format="json")
        assert response.status_code == 403


# ===========================================================================
# Update
# ===========================================================================


class TestLegalHoldUpdate:
    @pytest.mark.django_db
    def test_update_hold(self, client, staff_user, hold):
        client.force_authenticate(user=staff_user)
        response = client.patch(
            f"{HOLDS_URL}{hold.pk}/",
            {"name": "Updated Hold"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["name"] == "Updated Hold"

    @pytest.mark.django_db
    def test_update_hold_description(self, client, staff_user, hold):
        client.force_authenticate(user=staff_user)
        response = client.patch(
            f"{HOLDS_URL}{hold.pk}/",
            {"description": "Updated description"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["description"] == "Updated description"


# ===========================================================================
# Retrieve
# ===========================================================================


class TestLegalHoldRetrieve:
    @pytest.mark.django_db
    def test_retrieve_hold(self, client, staff_user, hold):
        client.force_authenticate(user=staff_user)
        response = client.get(f"{HOLDS_URL}{hold.pk}/")
        assert response.status_code == 200
        assert response.data["name"] == "Test Hold"
        assert response.data["matter_number"] == "CASE-001"
        assert "criteria_count" in response.data
        assert "custodian_count" in response.data
        assert "document_count" in response.data


# ===========================================================================
# Activate Action
# ===========================================================================


class TestLegalHoldActivate:
    @pytest.mark.django_db
    def test_activate_hold(self, client, staff_user, hold, document):
        LegalHoldCriteria.objects.create(
            hold=hold,
            criteria_type="specific_documents",
            value={"document_ids": [document.pk]},
        )
        client.force_authenticate(user=staff_user)
        with patch(PATCH_SEND_MAIL):
            response = client.post(f"{HOLDS_URL}{hold.pk}/activate/")
        assert response.status_code == 200
        assert response.data["status"] == "activated"
        assert response.data["documents_captured"] == 1
        assert response.data["hold"]["status"] == ACTIVE

    @pytest.mark.django_db
    def test_activate_already_active_hold(self, client, staff_user, active_hold):
        client.force_authenticate(user=staff_user)
        response = client.post(f"{HOLDS_URL}{active_hold.pk}/activate/")
        assert response.status_code == 400
        assert "Cannot activate" in response.data["error"]


# ===========================================================================
# Release Action
# ===========================================================================


class TestLegalHoldRelease:
    @pytest.mark.django_db
    def test_release_hold(self, client, staff_user, active_hold):
        client.force_authenticate(user=staff_user)
        response = client.post(
            f"{HOLDS_URL}{active_hold.pk}/release/",
            {"reason": "Case resolved"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "released"
        assert response.data["hold"]["release_reason"] == "Case resolved"

    @pytest.mark.django_db
    def test_release_draft_hold_fails(self, client, staff_user, hold):
        client.force_authenticate(user=staff_user)
        response = client.post(
            f"{HOLDS_URL}{hold.pk}/release/",
            {"reason": "test"},
            format="json",
        )
        assert response.status_code == 400
        assert "Cannot release" in response.data["error"]

    @pytest.mark.django_db
    def test_release_hold_empty_reason(self, client, staff_user, active_hold):
        client.force_authenticate(user=staff_user)
        response = client.post(
            f"{HOLDS_URL}{active_hold.pk}/release/",
            {},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "released"


# ===========================================================================
# Documents List
# ===========================================================================


class TestLegalHoldDocuments:
    @pytest.mark.django_db
    def test_list_documents(self, client, staff_user, active_hold, document):
        client.force_authenticate(user=staff_user)
        response = client.get(f"{HOLDS_URL}{active_hold.pk}/documents/")
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["document_title"] == "Test Doc"


# ===========================================================================
# Custodians List
# ===========================================================================


class TestLegalHoldCustodians:
    @pytest.mark.django_db
    def test_list_custodians(self, client, staff_user, hold):
        LegalHoldCustodian.objects.create(hold=hold, user=staff_user)
        client.force_authenticate(user=staff_user)
        response = client.get(f"{HOLDS_URL}{hold.pk}/custodians/")
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["username"] == "staffuser"

    @pytest.mark.django_db
    def test_list_custodians_empty(self, client, staff_user, hold):
        client.force_authenticate(user=staff_user)
        response = client.get(f"{HOLDS_URL}{hold.pk}/custodians/")
        assert response.status_code == 200
        assert len(response.data) == 0


# ===========================================================================
# Acknowledge Endpoint
# ===========================================================================


class TestCustodianAcknowledge:
    ACKNOWLEDGE_URL = "/api/v1/legal-holds/{hold_id}/acknowledge/"

    @pytest.mark.django_db
    def test_acknowledge_success(self, client, staff_user, hold):
        LegalHoldCustodian.objects.create(hold=hold, user=staff_user)
        client.force_authenticate(user=staff_user)
        url = self.ACKNOWLEDGE_URL.format(hold_id=hold.pk)
        response = client.post(url, {}, format="json")
        assert response.status_code == 200
        assert response.data["status"] == "acknowledged"
        assert response.data["acknowledged_at"] is not None

    @pytest.mark.django_db
    def test_acknowledge_already_acknowledged(self, client, staff_user, hold):
        from django.utils import timezone

        custodian = LegalHoldCustodian.objects.create(
            hold=hold, user=staff_user, acknowledged=True, acknowledged_at=timezone.now()
        )
        client.force_authenticate(user=staff_user)
        url = self.ACKNOWLEDGE_URL.format(hold_id=hold.pk)
        response = client.post(url, {}, format="json")
        assert response.status_code == 200
        assert response.data["status"] == "already_acknowledged"

    @pytest.mark.django_db
    def test_acknowledge_not_custodian(self, client, non_staff_user, hold):
        client.force_authenticate(user=non_staff_user)
        url = self.ACKNOWLEDGE_URL.format(hold_id=hold.pk)
        response = client.post(url, {}, format="json")
        assert response.status_code == 404
        assert "not a custodian" in response.data["error"]

    @pytest.mark.django_db
    def test_acknowledge_unauthenticated(self, client, hold):
        url = self.ACKNOWLEDGE_URL.format(hold_id=hold.pk)
        response = client.post(url, {}, format="json")
        assert response.status_code in (401, 403)


# ===========================================================================
# Notify Action
# ===========================================================================


class TestLegalHoldNotify:
    @pytest.mark.django_db
    def test_notify_active_hold(self, client, staff_user, active_hold):
        client.force_authenticate(user=staff_user)
        with patch(PATCH_SEND_MAIL):
            response = client.post(f"{HOLDS_URL}{active_hold.pk}/notify/")
        assert response.status_code == 200
        assert response.data["status"] == "notifications_queued"

    @pytest.mark.django_db
    def test_notify_draft_hold_fails(self, client, staff_user, hold):
        client.force_authenticate(user=staff_user)
        response = client.post(f"{HOLDS_URL}{hold.pk}/notify/")
        assert response.status_code == 400
        assert "active" in response.data["error"].lower()


# ===========================================================================
# Export Action
# ===========================================================================


class TestLegalHoldExport:
    @pytest.mark.django_db
    def test_export_hold(self, client, staff_user, hold):
        LegalHoldCriteria.objects.create(
            hold=hold, criteria_type="tag", value={"tag_ids": [1]}
        )
        LegalHoldCustodian.objects.create(hold=hold, user=staff_user)
        client.force_authenticate(user=staff_user)
        response = client.get(f"{HOLDS_URL}{hold.pk}/export/")
        assert response.status_code == 200
        assert "criteria" in response.data
        assert "custodians" in response.data
        assert "documents" in response.data
        assert response.data["name"] == "Test Hold"

    @pytest.mark.django_db
    def test_export_hold_non_staff_forbidden(self, client, non_staff_user, hold):
        client.force_authenticate(user=non_staff_user)
        response = client.get(f"{HOLDS_URL}{hold.pk}/export/")
        assert response.status_code == 403


# ===========================================================================
# Delete
# ===========================================================================


class TestLegalHoldDelete:
    @pytest.mark.django_db
    def test_delete_hold(self, client, staff_user, hold):
        client.force_authenticate(user=staff_user)
        response = client.delete(f"{HOLDS_URL}{hold.pk}/")
        assert response.status_code == 204
        assert not LegalHold.objects.filter(pk=hold.pk).exists()

    @pytest.mark.django_db
    def test_delete_hold_non_staff_forbidden(self, client, non_staff_user, hold):
        client.force_authenticate(user=non_staff_user)
        response = client.delete(f"{HOLDS_URL}{hold.pk}/")
        assert response.status_code == 403

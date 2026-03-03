"""Tests for physical_records API views."""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from physical_records.constants import (
    BUILDING,
    CHECKED_OUT,
    GOOD,
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

LOCATIONS_URL = "/api/v1/physical-locations/"
RECORDS_URL = "/api/v1/physical-records/"
CHARGE_OUTS_URL = "/api/v1/charge-outs/"
OVERDUE_URL = "/api/v1/charge-outs/overdue/"


@pytest.fixture
def client():
    return APIClient()


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
        name="HQ", location_type=BUILDING
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


@pytest.fixture
def physical_record2(document2, shelf, user):
    return PhysicalRecord.objects.create(
        document=document2,
        location=shelf,
        barcode="REC-002",
        condition=GOOD,
        created_by=user,
    )


# ===========================================================================
# PhysicalLocation CRUD
# ===========================================================================


class TestPhysicalLocationViewSet:
    @pytest.mark.django_db
    def test_list_locations(self, client, user, building):
        client.force_authenticate(user=user)
        response = client.get(LOCATIONS_URL)
        assert response.status_code == 200
        data = response.data.get("results", response.data)
        assert len(data) >= 1

    @pytest.mark.django_db
    def test_create_location(self, client, user):
        client.force_authenticate(user=user)
        data = {
            "name": "New Building",
            "location_type": BUILDING,
        }
        response = client.post(LOCATIONS_URL, data, format="json")
        assert response.status_code == 201
        assert response.data["name"] == "New Building"
        assert response.data["location_type"] == BUILDING

    @pytest.mark.django_db
    def test_create_location_with_parent(self, client, user, building):
        client.force_authenticate(user=user)
        data = {
            "name": "Room 202",
            "location_type": ROOM,
            "parent": building.pk,
        }
        response = client.post(LOCATIONS_URL, data, format="json")
        assert response.status_code == 201
        assert response.data["parent"] == building.pk

    @pytest.mark.django_db
    def test_retrieve_location(self, client, user, building):
        client.force_authenticate(user=user)
        response = client.get(f"{LOCATIONS_URL}{building.pk}/")
        assert response.status_code == 200
        assert response.data["name"] == "HQ"
        assert "children_count" in response.data

    @pytest.mark.django_db
    def test_update_location(self, client, user, building):
        client.force_authenticate(user=user)
        response = client.patch(
            f"{LOCATIONS_URL}{building.pk}/",
            {"name": "Updated HQ"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["name"] == "Updated HQ"

    @pytest.mark.django_db
    def test_delete_location(self, client, user, building):
        client.force_authenticate(user=user)
        response = client.delete(f"{LOCATIONS_URL}{building.pk}/")
        assert response.status_code == 204
        assert not PhysicalLocation.objects.filter(pk=building.pk).exists()

    @pytest.mark.django_db
    def test_tree_endpoint(self, client, user, building, room, shelf):
        client.force_authenticate(user=user)
        response = client.get(f"{LOCATIONS_URL}tree/")
        assert response.status_code == 200
        assert len(response.data) >= 1
        # Root node should have children
        root = response.data[0]
        assert root["name"] == "HQ"
        assert "children" in root
        assert len(root["children"]) >= 1

    @pytest.mark.django_db
    def test_unauthenticated_access_denied(self, client):
        response = client.get(LOCATIONS_URL)
        assert response.status_code in (401, 403)


# ===========================================================================
# PhysicalRecord CRUD
# ===========================================================================


class TestPhysicalRecordViewSet:
    @pytest.mark.django_db
    def test_list_records(self, client, user, physical_record):
        client.force_authenticate(user=user)
        response = client.get(RECORDS_URL)
        assert response.status_code == 200
        data = response.data.get("results", response.data)
        assert len(data) >= 1

    @pytest.mark.django_db
    def test_create_record(self, client, user, document2, shelf):
        client.force_authenticate(user=user)
        data = {
            "document": document2.pk,
            "location": shelf.pk,
            "barcode": "REC-NEW",
            "condition": GOOD,
            "position": "Row 3",
        }
        response = client.post(RECORDS_URL, data, format="json")
        assert response.status_code == 201
        assert response.data["barcode"] == "REC-NEW"

    @pytest.mark.django_db
    def test_create_record_updates_location_count(self, client, user, document2, shelf):
        client.force_authenticate(user=user)
        initial_count = shelf.current_count
        data = {
            "document": document2.pk,
            "location": shelf.pk,
            "barcode": "REC-NEW2",
            "condition": GOOD,
        }
        client.post(RECORDS_URL, data, format="json")
        shelf.refresh_from_db()
        assert shelf.current_count == initial_count + 1

    @pytest.mark.django_db
    def test_retrieve_record(self, client, user, physical_record):
        client.force_authenticate(user=user)
        response = client.get(f"{RECORDS_URL}{physical_record.pk}/")
        assert response.status_code == 200
        assert response.data["barcode"] == "REC-001"
        assert response.data["document_title"] == "Test Doc"
        assert response.data["location_name"] != ""

    @pytest.mark.django_db
    def test_update_record(self, client, user, physical_record):
        client.force_authenticate(user=user)
        response = client.patch(
            f"{RECORDS_URL}{physical_record.pk}/",
            {"condition": "poor", "notes": "Water damage"},
            format="json",
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_delete_record(self, client, user, physical_record):
        client.force_authenticate(user=user)
        response = client.delete(f"{RECORDS_URL}{physical_record.pk}/")
        assert response.status_code == 204
        assert not PhysicalRecord.objects.filter(pk=physical_record.pk).exists()

    @pytest.mark.django_db
    def test_unauthenticated_access_denied(self, client):
        response = client.get(RECORDS_URL)
        assert response.status_code in (401, 403)


# ===========================================================================
# Charge-Out (check out a physical record)
# ===========================================================================


class TestChargeOutView:
    def _charge_out_url(self, document_id):
        return f"/api/v1/documents/{document_id}/charge-out/"

    @pytest.mark.django_db
    def test_charge_out(self, client, user, document, physical_record):
        client.force_authenticate(user=user)
        expected = timezone.now() + timezone.timedelta(days=7)
        data = {
            "expected_return": expected.isoformat(),
            "notes": "For review",
        }
        response = client.post(
            self._charge_out_url(document.pk), data, format="json"
        )
        assert response.status_code == 201
        assert response.data["status"] == CHECKED_OUT
        assert response.data["notes"] == "For review"

    @pytest.mark.django_db
    def test_charge_out_updates_location_count(
        self, client, user, document, physical_record, shelf
    ):
        shelf.current_count = 5
        shelf.save()

        client.force_authenticate(user=user)
        data = {
            "expected_return": (
                timezone.now() + timezone.timedelta(days=7)
            ).isoformat(),
        }
        client.post(self._charge_out_url(document.pk), data, format="json")
        shelf.refresh_from_db()
        assert shelf.current_count == 4

    @pytest.mark.django_db
    def test_charge_out_already_checked_out(
        self, client, user, document, physical_record
    ):
        ChargeOut.objects.create(
            physical_record=physical_record,
            user=user,
            expected_return=timezone.now() + timezone.timedelta(days=7),
            status=CHECKED_OUT,
        )
        client.force_authenticate(user=user)
        data = {
            "expected_return": (
                timezone.now() + timezone.timedelta(days=7)
            ).isoformat(),
        }
        response = client.post(
            self._charge_out_url(document.pk), data, format="json"
        )
        assert response.status_code == 400
        assert "already checked out" in response.data["error"]

    @pytest.mark.django_db
    def test_charge_out_nonexistent_document(self, client, user):
        client.force_authenticate(user=user)
        data = {
            "expected_return": (
                timezone.now() + timezone.timedelta(days=7)
            ).isoformat(),
        }
        response = client.post(
            self._charge_out_url(99999), data, format="json"
        )
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_charge_out_unauthenticated(self, client, document):
        data = {
            "expected_return": (
                timezone.now() + timezone.timedelta(days=7)
            ).isoformat(),
        }
        response = client.post(
            self._charge_out_url(document.pk), data, format="json"
        )
        assert response.status_code in (401, 403)


# ===========================================================================
# Charge-In (return a physical record)
# ===========================================================================


class TestChargeInView:
    def _charge_in_url(self, document_id):
        return f"/api/v1/documents/{document_id}/charge-in/"

    @pytest.mark.django_db
    def test_charge_in(self, client, user, document, physical_record):
        ChargeOut.objects.create(
            physical_record=physical_record,
            user=user,
            expected_return=timezone.now() + timezone.timedelta(days=7),
            status=CHECKED_OUT,
        )
        client.force_authenticate(user=user)
        response = client.post(
            self._charge_in_url(document.pk), {"notes": "Returned"}, format="json"
        )
        assert response.status_code == 200
        assert response.data["status"] == RETURNED
        assert response.data["returned_at"] is not None

    @pytest.mark.django_db
    def test_charge_in_updates_location_count(
        self, client, user, document, physical_record, shelf
    ):
        shelf.current_count = 4
        shelf.save()
        ChargeOut.objects.create(
            physical_record=physical_record,
            user=user,
            expected_return=timezone.now() + timezone.timedelta(days=7),
            status=CHECKED_OUT,
        )
        client.force_authenticate(user=user)
        client.post(self._charge_in_url(document.pk), {}, format="json")
        shelf.refresh_from_db()
        assert shelf.current_count == 5

    @pytest.mark.django_db
    def test_charge_in_not_checked_out(
        self, client, user, document, physical_record
    ):
        client.force_authenticate(user=user)
        response = client.post(
            self._charge_in_url(document.pk), {}, format="json"
        )
        assert response.status_code == 400
        assert "not currently checked out" in response.data["error"]


# ===========================================================================
# Barcode Checkout
# ===========================================================================


class TestBarcodeCheckoutView:
    def _barcode_url(self, record_pk):
        return f"/api/v1/physical-records/{record_pk}/barcode-checkout/"

    @pytest.mark.django_db
    def test_barcode_checkout(self, client, user, physical_record):
        client.force_authenticate(user=user)
        data = {
            "barcode": "REC-001",
            "expected_return": (
                timezone.now() + timezone.timedelta(days=5)
            ).isoformat(),
        }
        response = client.post(
            self._barcode_url(physical_record.pk), data, format="json"
        )
        assert response.status_code == 201
        assert response.data["status"] == CHECKED_OUT

    @pytest.mark.django_db
    def test_barcode_checkout_wrong_barcode(self, client, user, physical_record):
        client.force_authenticate(user=user)
        data = {
            "barcode": "WRONG-BARCODE",
            "expected_return": (
                timezone.now() + timezone.timedelta(days=5)
            ).isoformat(),
        }
        response = client.post(
            self._barcode_url(physical_record.pk), data, format="json"
        )
        assert response.status_code == 400
        assert "does not match" in response.data["error"]

    @pytest.mark.django_db
    def test_barcode_checkout_already_checked_out(
        self, client, user, physical_record
    ):
        ChargeOut.objects.create(
            physical_record=physical_record,
            user=user,
            expected_return=timezone.now() + timezone.timedelta(days=7),
            status=CHECKED_OUT,
        )
        client.force_authenticate(user=user)
        data = {
            "barcode": "REC-001",
            "expected_return": (
                timezone.now() + timezone.timedelta(days=5)
            ).isoformat(),
        }
        response = client.post(
            self._barcode_url(physical_record.pk), data, format="json"
        )
        assert response.status_code == 400
        assert "already checked out" in response.data["error"]


# ===========================================================================
# Charge-Out List with Filters
# ===========================================================================


class TestChargeOutListView:
    @pytest.mark.django_db
    def test_list_charge_outs(self, client, user, physical_record):
        ChargeOut.objects.create(
            physical_record=physical_record,
            user=user,
            expected_return=timezone.now() + timezone.timedelta(days=7),
            status=CHECKED_OUT,
        )
        client.force_authenticate(user=user)
        response = client.get(CHARGE_OUTS_URL)
        assert response.status_code == 200
        assert len(response.data) >= 1

    @pytest.mark.django_db
    def test_list_charge_outs_filter_by_status(
        self, client, user, physical_record
    ):
        ChargeOut.objects.create(
            physical_record=physical_record,
            user=user,
            expected_return=timezone.now() + timezone.timedelta(days=7),
            status=CHECKED_OUT,
        )
        client.force_authenticate(user=user)
        response = client.get(f"{CHARGE_OUTS_URL}?status={CHECKED_OUT}")
        assert response.status_code == 200
        assert len(response.data) >= 1

        response = client.get(f"{CHARGE_OUTS_URL}?status={RETURNED}")
        assert response.status_code == 200
        assert len(response.data) == 0

    @pytest.mark.django_db
    def test_list_charge_outs_filter_by_user(
        self, client, user, physical_record
    ):
        ChargeOut.objects.create(
            physical_record=physical_record,
            user=user,
            expected_return=timezone.now() + timezone.timedelta(days=7),
            status=CHECKED_OUT,
        )
        client.force_authenticate(user=user)
        response = client.get(f"{CHARGE_OUTS_URL}?user={user.pk}")
        assert response.status_code == 200
        assert len(response.data) >= 1

    @pytest.mark.django_db
    def test_list_charge_outs_unauthenticated(self, client):
        response = client.get(CHARGE_OUTS_URL)
        assert response.status_code in (401, 403)


# ===========================================================================
# Overdue Charge-Outs
# ===========================================================================


class TestOverdueChargeOutView:
    @pytest.mark.django_db
    def test_overdue_list(self, client, user, physical_record):
        ChargeOut.objects.create(
            physical_record=physical_record,
            user=user,
            expected_return=timezone.now() - timezone.timedelta(days=1),
            status=CHECKED_OUT,
        )
        client.force_authenticate(user=user)
        response = client.get(OVERDUE_URL)
        assert response.status_code == 200
        assert len(response.data) >= 1

    @pytest.mark.django_db
    def test_overdue_list_excludes_returned(self, client, user, physical_record):
        ChargeOut.objects.create(
            physical_record=physical_record,
            user=user,
            expected_return=timezone.now() - timezone.timedelta(days=1),
            status=RETURNED,
            returned_at=timezone.now(),
        )
        client.force_authenticate(user=user)
        response = client.get(OVERDUE_URL)
        assert response.status_code == 200
        assert len(response.data) == 0

    @pytest.mark.django_db
    def test_overdue_list_excludes_future_expected(
        self, client, user, physical_record
    ):
        ChargeOut.objects.create(
            physical_record=physical_record,
            user=user,
            expected_return=timezone.now() + timezone.timedelta(days=7),
            status=CHECKED_OUT,
        )
        client.force_authenticate(user=user)
        response = client.get(OVERDUE_URL)
        assert response.status_code == 200
        assert len(response.data) == 0


# ===========================================================================
# Destruction Certificate
# ===========================================================================


class TestDestructionCertificateView:
    def _cert_url(self, record_pk):
        return f"/api/v1/physical-records/{record_pk}/destruction-certificate/"

    @pytest.mark.django_db
    def test_create_destruction_certificate(
        self, client, user, physical_record
    ):
        client.force_authenticate(user=user)
        data = {
            "method": SHREDDING,
            "witness": "Jane Doe",
            "notes": "Destroyed per retention policy",
        }
        response = client.post(
            self._cert_url(physical_record.pk), data, format="json"
        )
        assert response.status_code == 201
        assert response.data["method"] == SHREDDING
        assert response.data["witness"] == "Jane Doe"
        assert response.data["destroyed_at"] is not None
        assert response.data["destroyed_by"] == user.pk

    @pytest.mark.django_db
    def test_create_destruction_certificate_nonexistent(self, client, user):
        client.force_authenticate(user=user)
        data = {"method": SHREDDING}
        response = client.post(
            self._cert_url(99999), data, format="json"
        )
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_create_destruction_certificate_unauthenticated(
        self, client, physical_record
    ):
        data = {"method": SHREDDING}
        response = client.post(
            self._cert_url(physical_record.pk), data, format="json"
        )
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    def test_create_destruction_certificate_missing_method(
        self, client, user, physical_record
    ):
        client.force_authenticate(user=user)
        response = client.post(
            self._cert_url(physical_record.pk), {}, format="json"
        )
        assert response.status_code == 400

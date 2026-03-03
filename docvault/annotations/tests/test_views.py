"""Tests for the annotations app API views."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from annotations.constants import (
    HIGHLIGHT,
    RECTANGLE,
    STICKY_NOTE,
    UNDERLINE,
)
from annotations.models import Annotation, AnnotationReply
from documents.models import Document

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="otheruser", password="testpass456")


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username="staffuser", password="testpass789", is_staff=True,
    )


@pytest.fixture
def document(user):
    return Document.objects.create(
        title="Annotation View Test Doc",
        filename="annot_view_test_doc.pdf",
        owner=user,
        page_count=5,
    )


@pytest.fixture
def annotation(document, user):
    return Annotation.objects.create(
        document=document,
        page=1,
        annotation_type=HIGHLIGHT,
        coordinates={"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.02},
        content="",
        color="#FFFF00",
        opacity=0.3,
        author=user,
        created_by=user,
    )


@pytest.fixture
def private_annotation(document, user):
    return Annotation.objects.create(
        document=document,
        page=2,
        annotation_type=STICKY_NOTE,
        coordinates={"x": 0.5, "y": 0.5},
        content="Private note",
        author=user,
        is_private=True,
        created_by=user,
    )


@pytest.fixture
def reply(annotation, other_user):
    return AnnotationReply.objects.create(
        annotation=annotation,
        author=other_user,
        text="I agree with this.",
    )


def _annotation_url(document_id, pk=None):
    base = f"/api/v1/documents/{document_id}/annotations/"
    if pk is not None:
        return f"{base}{pk}/"
    return base


def _reply_url(document_id, annotation_id):
    return f"/api/v1/documents/{document_id}/annotations/{annotation_id}/replies/"


def _export_url(document_id):
    return f"/api/v1/documents/{document_id}/annotations/export/"


# ===========================================================================
# Annotation List & Create
# ===========================================================================


class TestAnnotationList:
    """Tests for GET /api/v1/documents/{id}/annotations/."""

    @pytest.mark.django_db
    def test_list_annotations(self, client, user, document, annotation):
        client.force_authenticate(user=user)
        response = client.get(_annotation_url(document.pk))
        assert response.status_code == 200
        assert len(response.data) >= 1

    @pytest.mark.django_db
    def test_list_includes_replies(self, client, user, document, annotation, reply):
        client.force_authenticate(user=user)
        response = client.get(_annotation_url(document.pk))
        assert response.status_code == 200
        annot_data = response.data[0]
        assert "replies" in annot_data
        assert len(annot_data["replies"]) >= 1

    @pytest.mark.django_db
    def test_list_filter_by_page(self, client, user, document, annotation):
        # Annotation is on page 1
        Annotation.objects.create(
            document=document, page=3, annotation_type=UNDERLINE,
            author=user, created_by=user,
        )
        client.force_authenticate(user=user)
        response = client.get(f"{_annotation_url(document.pk)}?page=1")
        assert response.status_code == 200
        pages = {a["page"] for a in response.data}
        assert pages == {1}

    @pytest.mark.django_db
    def test_list_filter_by_type(self, client, user, document, annotation):
        Annotation.objects.create(
            document=document, page=1, annotation_type=RECTANGLE,
            author=user, created_by=user,
        )
        client.force_authenticate(user=user)
        response = client.get(
            f"{_annotation_url(document.pk)}?type={HIGHLIGHT}"
        )
        assert response.status_code == 200
        types = {a["annotation_type"] for a in response.data}
        assert types == {HIGHLIGHT}

    @pytest.mark.django_db
    def test_list_filter_by_author(self, client, user, other_user, document, annotation):
        Annotation.objects.create(
            document=document, page=1, annotation_type=UNDERLINE,
            author=other_user, created_by=other_user,
        )
        client.force_authenticate(user=user)
        response = client.get(
            f"{_annotation_url(document.pk)}?author={user.pk}"
        )
        assert response.status_code == 200
        authors = {a["author"] for a in response.data}
        assert authors == {user.pk}

    @pytest.mark.django_db
    def test_private_annotations_hidden_from_non_author(
        self, client, other_user, document, annotation, private_annotation
    ):
        client.force_authenticate(user=other_user)
        response = client.get(_annotation_url(document.pk))
        assert response.status_code == 200
        # other_user should see the public annotation but not the private one
        ids = {a["id"] for a in response.data}
        assert annotation.pk in ids
        assert private_annotation.pk not in ids

    @pytest.mark.django_db
    def test_private_annotations_visible_to_author(
        self, client, user, document, annotation, private_annotation
    ):
        client.force_authenticate(user=user)
        response = client.get(_annotation_url(document.pk))
        ids = {a["id"] for a in response.data}
        assert annotation.pk in ids
        assert private_annotation.pk in ids

    @pytest.mark.django_db
    def test_private_annotations_visible_to_staff(
        self, client, staff_user, document, annotation, private_annotation
    ):
        client.force_authenticate(user=staff_user)
        response = client.get(_annotation_url(document.pk))
        ids = {a["id"] for a in response.data}
        assert private_annotation.pk in ids

    @pytest.mark.django_db
    def test_list_nonexistent_document_returns_404(self, client, user):
        client.force_authenticate(user=user)
        response = client.get(_annotation_url(99999))
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_list_unauthenticated_returns_401(self, client, document):
        response = client.get(_annotation_url(document.pk))
        assert response.status_code in (401, 403)


class TestAnnotationCreate:
    """Tests for POST /api/v1/documents/{id}/annotations/."""

    @pytest.mark.django_db
    def test_create_annotation(self, client, user, document):
        client.force_authenticate(user=user)
        data = {
            "page": 1,
            "annotation_type": HIGHLIGHT,
            "coordinates": {"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.02},
            "content": "",
            "color": "#FF0000",
            "opacity": 0.5,
            "is_private": False,
        }
        response = client.post(
            _annotation_url(document.pk), data, format="json",
        )
        assert response.status_code == 201
        assert response.data["annotation_type"] == HIGHLIGHT
        assert response.data["color"] == "#FF0000"
        assert response.data["author"] == user.pk

    @pytest.mark.django_db
    def test_create_sticky_note_with_content(self, client, user, document):
        client.force_authenticate(user=user)
        data = {
            "page": 2,
            "annotation_type": STICKY_NOTE,
            "coordinates": {"x": 0.5, "y": 0.5},
            "content": "This needs review",
            "is_private": True,
        }
        response = client.post(
            _annotation_url(document.pk), data, format="json",
        )
        assert response.status_code == 201
        assert response.data["content"] == "This needs review"
        assert response.data["is_private"] is True

    @pytest.mark.django_db
    def test_create_annotation_invalid_coordinates_returns_400(
        self, client, user, document
    ):
        client.force_authenticate(user=user)
        data = {
            "page": 1,
            "annotation_type": HIGHLIGHT,
            "coordinates": {"x": 1.5, "y": 0.2},  # out of range
        }
        response = client.post(
            _annotation_url(document.pk), data, format="json",
        )
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_create_annotation_unauthenticated(self, client, document):
        data = {
            "page": 1,
            "annotation_type": HIGHLIGHT,
            "coordinates": {"x": 0.1, "y": 0.2},
        }
        response = client.post(
            _annotation_url(document.pk), data, format="json",
        )
        assert response.status_code in (401, 403)


# ===========================================================================
# Annotation Retrieve, Update, Delete
# ===========================================================================


class TestAnnotationRetrieve:
    """Tests for GET /api/v1/documents/{id}/annotations/{pk}/."""

    @pytest.mark.django_db
    def test_retrieve_annotation(self, client, user, document, annotation):
        client.force_authenticate(user=user)
        response = client.get(_annotation_url(document.pk, annotation.pk))
        assert response.status_code == 200
        assert response.data["id"] == annotation.pk

    @pytest.mark.django_db
    def test_retrieve_private_annotation_by_non_author(
        self, client, other_user, document, private_annotation
    ):
        client.force_authenticate(user=other_user)
        response = client.get(
            _annotation_url(document.pk, private_annotation.pk)
        )
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_retrieve_private_annotation_by_staff(
        self, client, staff_user, document, private_annotation
    ):
        client.force_authenticate(user=staff_user)
        response = client.get(
            _annotation_url(document.pk, private_annotation.pk)
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_retrieve_nonexistent_returns_404(self, client, user, document):
        client.force_authenticate(user=user)
        response = client.get(_annotation_url(document.pk, 99999))
        assert response.status_code == 404


class TestAnnotationUpdate:
    """Tests for PATCH /api/v1/documents/{id}/annotations/{pk}/."""

    @pytest.mark.django_db
    def test_update_annotation_by_author(self, client, user, document, annotation):
        client.force_authenticate(user=user)
        data = {"color": "#00FF00", "opacity": 0.8}
        response = client.patch(
            _annotation_url(document.pk, annotation.pk), data, format="json",
        )
        assert response.status_code == 200
        assert response.data["color"] == "#00FF00"
        assert response.data["opacity"] == 0.8

    @pytest.mark.django_db
    def test_update_annotation_content(self, client, user, document, annotation):
        client.force_authenticate(user=user)
        data = {"content": "Updated content"}
        response = client.patch(
            _annotation_url(document.pk, annotation.pk), data, format="json",
        )
        assert response.status_code == 200
        assert response.data["content"] == "Updated content"

    @pytest.mark.django_db
    def test_non_author_cannot_update(
        self, client, other_user, document, annotation
    ):
        # other_user is not the author and not the document owner
        client.force_authenticate(user=other_user)
        data = {"color": "#0000FF"}
        response = client.patch(
            _annotation_url(document.pk, annotation.pk), data, format="json",
        )
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_document_owner_can_update(
        self, client, other_user, user, document
    ):
        # Create annotation by other_user on document owned by user
        annot = Annotation.objects.create(
            document=document, page=1, annotation_type=HIGHLIGHT,
            author=other_user, created_by=other_user,
        )
        client.force_authenticate(user=user)  # document owner
        data = {"color": "#0000FF"}
        response = client.patch(
            _annotation_url(document.pk, annot.pk), data, format="json",
        )
        assert response.status_code == 200


class TestAnnotationDelete:
    """Tests for DELETE /api/v1/documents/{id}/annotations/{pk}/."""

    @pytest.mark.django_db
    def test_delete_annotation_by_author(self, client, user, document, annotation):
        client.force_authenticate(user=user)
        response = client.delete(_annotation_url(document.pk, annotation.pk))
        assert response.status_code == 204
        assert not Annotation.objects.filter(pk=annotation.pk).exists()

    @pytest.mark.django_db
    def test_non_author_non_owner_cannot_delete(
        self, client, other_user, document, annotation
    ):
        client.force_authenticate(user=other_user)
        response = client.delete(_annotation_url(document.pk, annotation.pk))
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_document_owner_can_delete_any_annotation(
        self, client, user, other_user, document
    ):
        annot = Annotation.objects.create(
            document=document, page=1, annotation_type=HIGHLIGHT,
            author=other_user, created_by=other_user,
        )
        client.force_authenticate(user=user)  # document owner
        response = client.delete(_annotation_url(document.pk, annot.pk))
        assert response.status_code == 204

    @pytest.mark.django_db
    def test_staff_can_delete_any_annotation(
        self, client, staff_user, document, annotation
    ):
        client.force_authenticate(user=staff_user)
        response = client.delete(_annotation_url(document.pk, annotation.pk))
        assert response.status_code == 204

    @pytest.mark.django_db
    def test_delete_nonexistent_returns_404(self, client, user, document):
        client.force_authenticate(user=user)
        response = client.delete(_annotation_url(document.pk, 99999))
        assert response.status_code == 404


# ===========================================================================
# Annotation Replies
# ===========================================================================


class TestAnnotationReplies:
    """Tests for GET/POST /documents/{id}/annotations/{id}/replies/."""

    @pytest.mark.django_db
    def test_list_replies(self, client, user, document, annotation, reply):
        client.force_authenticate(user=user)
        response = client.get(_reply_url(document.pk, annotation.pk))
        assert response.status_code == 200
        assert len(response.data) >= 1
        assert response.data[0]["text"] == "I agree with this."

    @pytest.mark.django_db
    def test_create_reply(self, client, user, document, annotation):
        client.force_authenticate(user=user)
        data = {"text": "Good point!"}
        response = client.post(
            _reply_url(document.pk, annotation.pk), data, format="json",
        )
        assert response.status_code == 201
        assert response.data["text"] == "Good point!"

    @pytest.mark.django_db
    def test_create_reply_empty_text_returns_400(
        self, client, user, document, annotation
    ):
        client.force_authenticate(user=user)
        data = {"text": ""}
        response = client.post(
            _reply_url(document.pk, annotation.pk), data, format="json",
        )
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_reply_on_private_annotation_hidden_from_non_author(
        self, client, other_user, document, private_annotation
    ):
        client.force_authenticate(user=other_user)
        response = client.get(
            _reply_url(document.pk, private_annotation.pk),
        )
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_reply_unauthenticated(self, client, document, annotation):
        response = client.post(
            _reply_url(document.pk, annotation.pk),
            {"text": "hello"},
            format="json",
        )
        assert response.status_code in (401, 403)

    @pytest.mark.django_db
    def test_reply_nonexistent_annotation_returns_404(
        self, client, user, document
    ):
        client.force_authenticate(user=user)
        response = client.get(_reply_url(document.pk, 99999))
        assert response.status_code == 404


# ===========================================================================
# Export
# ===========================================================================


class TestAnnotationExport:
    """Tests for POST /api/v1/documents/{id}/annotations/export/."""

    @pytest.mark.django_db
    def test_export_annotations(self, client, user, document, annotation):
        client.force_authenticate(user=user)
        response = client.post(_export_url(document.pk), format="json")
        assert response.status_code == 200
        assert int(response.data["document_id"]) == document.pk
        assert response.data["annotation_count"] >= 1
        assert "annotations" in response.data

    @pytest.mark.django_db
    def test_export_excludes_private_for_non_author(
        self, client, other_user, document, annotation, private_annotation
    ):
        client.force_authenticate(user=other_user)
        response = client.post(_export_url(document.pk), format="json")
        assert response.status_code == 200
        ids = {a["id"] for a in response.data["annotations"]}
        assert annotation.pk in ids
        assert private_annotation.pk not in ids

    @pytest.mark.django_db
    def test_export_nonexistent_document_returns_404(self, client, user):
        client.force_authenticate(user=user)
        response = client.post(_export_url(99999), format="json")
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_export_unauthenticated(self, client, document):
        response = client.post(_export_url(document.pk), format="json")
        assert response.status_code in (401, 403)

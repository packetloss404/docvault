"""Tests for the annotations app models."""

import pytest
from django.contrib.auth import get_user_model

from annotations.constants import (
    FREEHAND,
    HIGHLIGHT,
    RECTANGLE,
    RUBBER_STAMP,
    STICKY_NOTE,
    STRIKETHROUGH,
    TEXT_BOX,
    UNDERLINE,
)
from annotations.models import Annotation, AnnotationReply
from documents.models import Document

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="otheruser", password="testpass456")


@pytest.fixture
def document(user):
    return Document.objects.create(
        title="Annotation Test Doc",
        filename="annot_test_doc.pdf",
        owner=user,
        page_count=10,
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
        text="I agree with this highlight.",
    )


# ---------------------------------------------------------------------------
# Annotation
# ---------------------------------------------------------------------------


class TestAnnotation:
    """Tests for the Annotation model."""

    @pytest.mark.django_db
    def test_create_annotation(self, annotation):
        assert annotation.pk is not None
        assert annotation.annotation_type == HIGHLIGHT
        assert annotation.page == 1

    @pytest.mark.django_db
    def test_str_representation(self, annotation):
        expected = f"highlight on page 1 of doc {annotation.document_id}"
        assert str(annotation) == expected

    @pytest.mark.django_db
    def test_default_color(self, document, user):
        a = Annotation.objects.create(
            document=document,
            page=1,
            annotation_type=HIGHLIGHT,
            author=user,
            created_by=user,
        )
        assert a.color == "#FFFF00"

    @pytest.mark.django_db
    def test_default_opacity(self, document, user):
        a = Annotation.objects.create(
            document=document,
            page=1,
            annotation_type=HIGHLIGHT,
            author=user,
            created_by=user,
        )
        assert a.opacity == 0.3

    @pytest.mark.django_db
    def test_default_is_private_false(self, annotation):
        assert annotation.is_private is False

    @pytest.mark.django_db
    def test_is_private_flag(self, private_annotation):
        assert private_annotation.is_private is True

    @pytest.mark.django_db
    def test_annotation_type_choices(self, document, user):
        for atype in [HIGHLIGHT, UNDERLINE, STRIKETHROUGH, STICKY_NOTE,
                       FREEHAND, RECTANGLE, TEXT_BOX, RUBBER_STAMP]:
            a = Annotation.objects.create(
                document=document,
                page=1,
                annotation_type=atype,
                author=user,
                created_by=user,
            )
            assert a.annotation_type == atype

    @pytest.mark.django_db
    def test_coordinates_json_field(self, annotation):
        assert isinstance(annotation.coordinates, dict)
        assert annotation.coordinates["x"] == 0.1

    @pytest.mark.django_db
    def test_content_default_empty(self, document, user):
        a = Annotation.objects.create(
            document=document,
            page=1,
            annotation_type=HIGHLIGHT,
            author=user,
            created_by=user,
        )
        assert a.content == ""

    @pytest.mark.django_db
    def test_ordering_by_created_at_descending(self, document, user):
        a1 = Annotation.objects.create(
            document=document, page=1, annotation_type=HIGHLIGHT,
            author=user, created_by=user,
        )
        a2 = Annotation.objects.create(
            document=document, page=2, annotation_type=UNDERLINE,
            author=user, created_by=user,
        )
        pks = list(Annotation.objects.values_list("pk", flat=True))
        assert pks.index(a2.pk) < pks.index(a1.pk)

    @pytest.mark.django_db
    def test_cascade_delete_document_removes_annotations(self, document, annotation):
        assert Annotation.objects.count() == 1
        document.hard_delete()
        assert Annotation.objects.count() == 0

    @pytest.mark.django_db
    def test_cascade_delete_author_removes_annotations(self, user, annotation):
        assert Annotation.objects.count() == 1
        user.delete()
        assert Annotation.objects.count() == 0

    @pytest.mark.django_db
    def test_auditable_timestamps(self, annotation):
        assert annotation.created_at is not None
        assert annotation.updated_at is not None


# ---------------------------------------------------------------------------
# AnnotationReply
# ---------------------------------------------------------------------------


class TestAnnotationReply:
    """Tests for the AnnotationReply model."""

    @pytest.mark.django_db
    def test_create_reply(self, reply):
        assert reply.pk is not None
        assert reply.text == "I agree with this highlight."

    @pytest.mark.django_db
    def test_str_representation(self, reply):
        assert f"Reply by {reply.author_id}" in str(reply)
        assert f"annotation {reply.annotation_id}" in str(reply)

    @pytest.mark.django_db
    def test_reply_created_at_auto_set(self, reply):
        assert reply.created_at is not None

    @pytest.mark.django_db
    def test_ordering_by_created_at_ascending(self, annotation, other_user):
        r1 = AnnotationReply.objects.create(
            annotation=annotation, author=other_user, text="First",
        )
        r2 = AnnotationReply.objects.create(
            annotation=annotation, author=other_user, text="Second",
        )
        replies = list(annotation.replies.all())
        assert replies[0].pk == r1.pk
        assert replies[1].pk == r2.pk

    @pytest.mark.django_db
    def test_cascade_delete_annotation_removes_replies(
        self, annotation, reply
    ):
        assert AnnotationReply.objects.count() == 1
        annotation.delete()
        assert AnnotationReply.objects.count() == 0

    @pytest.mark.django_db
    def test_cascade_delete_author_removes_replies(self, other_user, reply):
        assert AnnotationReply.objects.count() == 1
        other_user.delete()
        assert AnnotationReply.objects.count() == 0

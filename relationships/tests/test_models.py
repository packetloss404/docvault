"""Tests for the relationships app models."""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from documents.models import Document
from relationships.constants import BUILTIN_TYPES
from relationships.models import DocumentRelationship, RelationshipType

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def doc_a(user):
    return Document.objects.create(title="Document A", owner=user, created_by=user)


@pytest.fixture
def doc_b(user):
    return Document.objects.create(title="Document B", owner=user, created_by=user)


@pytest.fixture
def doc_c(user):
    return Document.objects.create(title="Document C", owner=user, created_by=user)


@pytest.fixture
def rel_type(db):
    return RelationshipType.objects.create(
        slug="test-type",
        label="Test Type",
        icon="bi-test",
        is_directional=True,
        is_builtin=False,
    )


@pytest.fixture
def builtin_type(db):
    return RelationshipType.objects.create(
        slug="builtin-test",
        label="Built-in Test",
        icon="bi-builtin",
        is_directional=True,
        is_builtin=True,
    )


class TestRelationshipType:
    """Tests for the RelationshipType model."""

    @pytest.mark.django_db
    def test_create_relationship_type(self, rel_type):
        assert rel_type.pk is not None
        assert rel_type.slug == "test-type"
        assert rel_type.label == "Test Type"
        assert rel_type.icon == "bi-test"
        assert rel_type.is_directional is True
        assert rel_type.is_builtin is False

    @pytest.mark.django_db
    def test_str_returns_label(self, rel_type):
        assert str(rel_type) == "Test Type"

    @pytest.mark.django_db
    def test_slug_uniqueness(self, rel_type):
        with pytest.raises(IntegrityError):
            RelationshipType.objects.create(
                slug="test-type",
                label="Another Type",
            )

    @pytest.mark.django_db
    def test_default_values(self):
        rt = RelationshipType.objects.create(slug="defaults", label="Defaults")
        assert rt.icon == "bi-link-45deg"
        assert rt.is_directional is True
        assert rt.is_builtin is False
        assert rt.description == ""

    @pytest.mark.django_db
    def test_ordering_by_label(self):
        RelationshipType.objects.create(slug="z-type", label="Zeta")
        RelationshipType.objects.create(slug="a-type", label="Alpha")
        RelationshipType.objects.create(slug="m-type", label="Mu")
        types = list(RelationshipType.objects.values_list("label", flat=True))
        assert types == sorted(types)


class TestSeedDefaults:
    """Tests for the RelationshipType.seed_defaults() class method."""

    @pytest.mark.django_db
    def test_seed_creates_all_builtin_types(self):
        RelationshipType.seed_defaults()
        assert RelationshipType.objects.count() == len(BUILTIN_TYPES)

    @pytest.mark.django_db
    def test_seed_types_are_builtin(self):
        RelationshipType.seed_defaults()
        for rt in RelationshipType.objects.all():
            assert rt.is_builtin is True

    @pytest.mark.django_db
    def test_seed_creates_correct_slugs(self):
        RelationshipType.seed_defaults()
        expected_slugs = {slug for slug, _, _, _ in BUILTIN_TYPES}
        actual_slugs = set(RelationshipType.objects.values_list("slug", flat=True))
        assert actual_slugs == expected_slugs

    @pytest.mark.django_db
    def test_seed_is_idempotent(self):
        RelationshipType.seed_defaults()
        count_first = RelationshipType.objects.count()
        RelationshipType.seed_defaults()
        count_second = RelationshipType.objects.count()
        assert count_first == count_second == len(BUILTIN_TYPES)

    @pytest.mark.django_db
    def test_seed_preserves_existing_edits(self):
        RelationshipType.seed_defaults()
        rt = RelationshipType.objects.get(slug="supersedes")
        rt.description = "Custom description"
        rt.save()

        RelationshipType.seed_defaults()
        rt.refresh_from_db()
        assert rt.description == "Custom description"

    @pytest.mark.django_db
    def test_seed_sets_correct_directionality(self):
        RelationshipType.seed_defaults()
        for slug, label, icon, is_directional in BUILTIN_TYPES:
            rt = RelationshipType.objects.get(slug=slug)
            assert rt.label == label
            assert rt.icon == icon
            assert rt.is_directional == is_directional


class TestDocumentRelationship:
    """Tests for the DocumentRelationship model."""

    @pytest.mark.django_db
    def test_create_relationship(self, doc_a, doc_b, rel_type):
        rel = DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=rel_type,
            notes="Test note",
        )
        assert rel.pk is not None
        assert rel.source_document == doc_a
        assert rel.target_document == doc_b
        assert rel.relationship_type == rel_type
        assert rel.notes == "Test note"

    @pytest.mark.django_db
    def test_str_representation(self, doc_a, doc_b, rel_type):
        rel = DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=rel_type,
        )
        expected = f"Document A --[Test Type]--> Document B"
        assert str(rel) == expected

    @pytest.mark.django_db
    def test_unique_constraint_source_target_type(self, doc_a, doc_b, rel_type):
        DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=rel_type,
        )
        with pytest.raises(IntegrityError):
            DocumentRelationship.objects.create(
                source_document=doc_a,
                target_document=doc_b,
                relationship_type=rel_type,
            )

    @pytest.mark.django_db
    def test_same_pair_different_type_allowed(self, doc_a, doc_b):
        type1 = RelationshipType.objects.create(slug="type-1", label="Type 1")
        type2 = RelationshipType.objects.create(slug="type-2", label="Type 2")
        DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=type1,
        )
        rel2 = DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=type2,
        )
        assert rel2.pk is not None

    @pytest.mark.django_db
    def test_reverse_direction_allowed(self, doc_a, doc_b, rel_type):
        DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=rel_type,
        )
        rel2 = DocumentRelationship.objects.create(
            source_document=doc_b,
            target_document=doc_a,
            relationship_type=rel_type,
        )
        assert rel2.pk is not None

    @pytest.mark.django_db
    def test_cascade_delete_source_document(self, doc_a, doc_b, rel_type, user):
        DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=rel_type,
        )
        assert DocumentRelationship.objects.count() == 1
        doc_a.hard_delete()
        assert DocumentRelationship.objects.count() == 0

    @pytest.mark.django_db
    def test_cascade_delete_target_document(self, doc_a, doc_b, rel_type, user):
        DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=rel_type,
        )
        assert DocumentRelationship.objects.count() == 1
        doc_b.hard_delete()
        assert DocumentRelationship.objects.count() == 0

    @pytest.mark.django_db
    def test_cascade_delete_relationship_type(self, doc_a, doc_b, rel_type):
        DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=rel_type,
        )
        assert DocumentRelationship.objects.count() == 1
        rel_type.delete()
        assert DocumentRelationship.objects.count() == 0

    @pytest.mark.django_db
    def test_outgoing_relationships_manager(self, doc_a, doc_b, doc_c, rel_type):
        DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=rel_type,
        )
        DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_c,
            relationship_type=rel_type,
        )
        assert doc_a.outgoing_relationships.count() == 2

    @pytest.mark.django_db
    def test_incoming_relationships_manager(self, doc_a, doc_b, doc_c, rel_type):
        DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_c,
            relationship_type=rel_type,
        )
        DocumentRelationship.objects.create(
            source_document=doc_b,
            target_document=doc_c,
            relationship_type=rel_type,
        )
        assert doc_c.incoming_relationships.count() == 2

    @pytest.mark.django_db
    def test_notes_defaults_to_empty(self, doc_a, doc_b, rel_type):
        rel = DocumentRelationship.objects.create(
            source_document=doc_a,
            target_document=doc_b,
            relationship_type=rel_type,
        )
        assert rel.notes == ""

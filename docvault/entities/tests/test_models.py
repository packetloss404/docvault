"""Tests for Entity models (EntityType, Entity)."""

import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError

from documents.models import Document
from entities.constants import DEFAULT_ENTITY_TYPES
from entities.models import Entity, EntityType


@pytest.fixture
def user(db):
    return User.objects.create_user(username="entityuser", password="testpass")


@pytest.fixture
def document(user):
    return Document.objects.create(
        title="Entity Test Doc",
        content="John Doe works at Acme Corp in New York.",
        owner=user,
    )


@pytest.fixture
def entity_type(db):
    return EntityType.objects.create(
        name="PERSON",
        label="Person",
        color="#0d6efd",
        icon="bi-person",
    )


@pytest.fixture
def entity(document, entity_type):
    return Entity.objects.create(
        document=document,
        entity_type=entity_type,
        value="John Doe",
        raw_value="John Doe",
        confidence=0.95,
        start_offset=0,
        end_offset=8,
    )


@pytest.mark.django_db
class TestEntityType:
    def test_create_entity_type(self, entity_type):
        assert entity_type.pk is not None
        assert entity_type.name == "PERSON"
        assert entity_type.label == "Person"
        assert entity_type.enabled is True

    def test_str_representation(self, entity_type):
        assert str(entity_type) == "Person"

    def test_unique_name_constraint(self, entity_type):
        with pytest.raises(IntegrityError):
            EntityType.objects.create(name="PERSON", label="Duplicate Person")

    def test_ordering_by_name(self):
        EntityType.objects.create(name="ZZZZZ", label="Z")
        EntityType.objects.create(name="AAAAA", label="A")
        EntityType.objects.create(name="MMMMM", label="M")
        names = list(EntityType.objects.values_list("name", flat=True))
        assert names == sorted(names)

    def test_default_values(self):
        et = EntityType.objects.create(name="CUSTOM_TYPE", label="Custom")
        assert et.color == "#6c757d"
        assert et.icon == "bi-tag"
        assert et.extraction_pattern == ""
        assert et.enabled is True

    def test_seed_defaults(self):
        EntityType.seed_defaults()
        for name, label, color, icon in DEFAULT_ENTITY_TYPES:
            et = EntityType.objects.get(name=name)
            assert et.label == label
            assert et.color == color
            assert et.icon == icon

    def test_seed_defaults_is_idempotent(self):
        EntityType.seed_defaults()
        count_first = EntityType.objects.count()
        EntityType.seed_defaults()
        count_second = EntityType.objects.count()
        assert count_first == count_second

    def test_seed_defaults_does_not_overwrite_existing(self):
        EntityType.objects.create(
            name="PERSON", label="Custom Person", color="#ffffff", icon="bi-x",
        )
        EntityType.seed_defaults()
        person = EntityType.objects.get(name="PERSON")
        # get_or_create should not overwrite existing
        assert person.label == "Custom Person"


@pytest.mark.django_db
class TestEntity:
    def test_create_entity(self, entity, document, entity_type):
        assert entity.pk is not None
        assert entity.document == document
        assert entity.entity_type == entity_type
        assert entity.value == "John Doe"
        assert entity.raw_value == "John Doe"
        assert entity.confidence == 0.95

    def test_str_representation(self, entity):
        s = str(entity)
        assert "PERSON" in s
        assert "John Doe" in s

    def test_default_values(self, document, entity_type):
        e = Entity.objects.create(
            document=document,
            entity_type=entity_type,
            value="Test",
            raw_value="Test",
        )
        assert e.confidence == 1.0
        assert e.start_offset == 0
        assert e.end_offset == 0
        assert e.page_number is None

    def test_cascade_delete_document(self, entity, document):
        assert Entity.objects.count() == 1
        document.hard_delete()
        assert Entity.objects.count() == 0

    def test_cascade_delete_entity_type(self, entity, entity_type):
        assert Entity.objects.count() == 1
        entity_type.delete()
        assert Entity.objects.count() == 0

    def test_ordering(self, document):
        type_person = EntityType.objects.create(name="PERSON_2", label="Person 2")
        type_org = EntityType.objects.create(name="ORG_2", label="Org 2")
        Entity.objects.create(
            document=document, entity_type=type_person,
            value="Zack", raw_value="Zack",
        )
        Entity.objects.create(
            document=document, entity_type=type_org,
            value="Alpha Corp", raw_value="Alpha Corp",
        )
        Entity.objects.create(
            document=document, entity_type=type_person,
            value="Alice", raw_value="Alice",
        )
        entities = list(Entity.objects.filter(document=document).values_list("value", flat=True))
        # Ordering is by entity_type name, then value
        assert entities[0] == "Alpha Corp"  # ORG_2 comes first

    def test_composite_index_exists(self):
        """The Meta.indexes should include [document, entity_type]."""
        index_fields = [idx.fields for idx in Entity._meta.indexes]
        assert ["document", "entity_type"] in index_fields

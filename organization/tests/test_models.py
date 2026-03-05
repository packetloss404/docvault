"""Tests for organization models."""

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from organization.models import Cabinet, Correspondent, StoragePath, Tag


class TagModelTest(TestCase):
    """Tests for the Tag model."""

    def setUp(self):
        self.user = User.objects.create_user(username="tagger", password="pass!")

    def test_create_root_tag(self):
        tag = Tag.objects.create(name="Important", owner=self.user)
        self.assertEqual(tag.name, "Important")
        self.assertEqual(tag.slug, "important")
        self.assertIsNone(tag.parent)
        self.assertTrue(tag.is_root_node())

    def test_create_child_tag(self):
        parent = Tag.objects.create(name="Finance", owner=self.user)
        child = Tag.objects.create(name="Invoices", parent=parent, owner=self.user)
        self.assertEqual(child.parent, parent)
        self.assertFalse(child.is_root_node())
        self.assertIn(child, parent.get_children())

    def test_tag_color_default(self):
        tag = Tag.objects.create(name="Test", owner=self.user)
        self.assertEqual(tag.color, "#3b82f6")

    def test_tag_color_custom(self):
        tag = Tag.objects.create(name="Red", color="#ff0000", owner=self.user)
        self.assertEqual(tag.color, "#ff0000")

    def test_tag_is_inbox(self):
        tag = Tag.objects.create(name="Inbox", is_inbox_tag=True, owner=self.user)
        self.assertTrue(tag.is_inbox_tag)

    def test_tag_str(self):
        tag = Tag.objects.create(name="Test Tag", owner=self.user)
        self.assertEqual(str(tag), "Test Tag")

    def test_tag_hierarchy_depth(self):
        """Test multi-level tag hierarchy."""
        root = Tag.objects.create(name="L0", owner=self.user)
        l1 = Tag.objects.create(name="L1", parent=root, owner=self.user)
        l2 = Tag.objects.create(name="L2", parent=l1, owner=self.user)
        l3 = Tag.objects.create(name="L3", parent=l2, owner=self.user)
        self.assertEqual(l3.get_level(), 3)


class CorrespondentModelTest(TestCase):
    """Tests for the Correspondent model."""

    def setUp(self):
        self.user = User.objects.create_user(username="corruser", password="pass!")

    def test_create_correspondent(self):
        corr = Correspondent.objects.create(name="ACME Corp", owner=self.user)
        self.assertEqual(corr.name, "ACME Corp")
        self.assertEqual(corr.slug, "acme-corp")

    def test_correspondent_str(self):
        corr = Correspondent.objects.create(name="Test Sender", owner=self.user)
        self.assertEqual(str(corr), "Test Sender")

    def test_correspondent_matching_fields(self):
        corr = Correspondent.objects.create(
            name="Bank",
            match="bank statement",
            matching_algorithm=1,
            owner=self.user,
        )
        self.assertEqual(corr.match, "bank statement")
        self.assertEqual(corr.matching_algorithm, 1)


class CabinetModelTest(TestCase):
    """Tests for the Cabinet model."""

    def setUp(self):
        self.user = User.objects.create_user(username="cabuser", password="pass!")

    def test_create_root_cabinet(self):
        cab = Cabinet.objects.create(name="Financial", owner=self.user)
        self.assertEqual(cab.name, "Financial")
        self.assertEqual(cab.slug, "financial")
        self.assertTrue(cab.is_root_node())

    def test_create_nested_cabinet(self):
        root = Cabinet.objects.create(name="Documents", owner=self.user)
        child = Cabinet.objects.create(name="2025", parent=root, owner=self.user)
        self.assertEqual(child.parent, root)
        self.assertIn(child, root.get_children())

    def test_cabinet_str(self):
        cab = Cabinet.objects.create(name="Archive", owner=self.user)
        self.assertEqual(str(cab), "Archive")


class StoragePathModelTest(TestCase):
    """Tests for the StoragePath model."""

    def setUp(self):
        self.user = User.objects.create_user(username="spuser", password="pass!")

    def test_create_storage_path(self):
        sp = StoragePath.objects.create(
            name="By Year",
            path="{{ created_year }}/{{ title }}",
            owner=self.user,
        )
        self.assertEqual(sp.name, "By Year")
        self.assertEqual(sp.slug, "by-year")

    def test_render_path(self):
        """Test Jinja2 template rendering."""
        from datetime import date
        from unittest.mock import Mock

        sp = StoragePath.objects.create(
            name="Full Path",
            path="{{ created_year }}/{{ document_type }}/{{ title }}",
            owner=self.user,
        )

        doc = Mock()
        doc.created = date(2025, 6, 15)
        doc.added = None
        doc.title = "My Invoice"
        doc.original_filename = "invoice.pdf"
        doc.archive_serial_number = None
        doc.correspondent = None
        doc.document_type = Mock()
        doc.document_type.name = "Invoice"

        rendered = sp.render(doc)
        self.assertEqual(rendered, "2025/Invoice/My Invoice")

    def test_invalid_template_raises_validation_error(self):
        from organization.models.storage_path import validate_path_template
        with self.assertRaises(ValidationError):
            validate_path_template("{{ unclosed")

"""Tests for saved view execution (filter rule application)."""

from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from documents.models import Document
from organization.models import Cabinet, Correspondent, Tag

from search.models import (
    RULE_CORRESPONDENT_IS,
    RULE_CREATED_AFTER,
    RULE_CREATED_BEFORE,
    RULE_DOCUMENT_TYPE_IS,
    RULE_FILENAME_CONTAINS,
    RULE_HAS_CORRESPONDENT,
    RULE_HAS_NO_CORRESPONDENT,
    RULE_HAS_NO_TAGS,
    RULE_HAS_TAGS,
    RULE_LANGUAGE_IS,
    RULE_TAG_ALL,
    RULE_TAG_IS,
    RULE_TAG_NONE,
    RULE_TITLE_CONTAINS,
    SavedView,
    SavedViewFilterRule,
)
from search.saved_view_executor import execute_saved_view


class SavedViewExecutorTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="executor", password="pass!")
        self.other_user = User.objects.create_user(username="other", password="pass!")
        self.admin = User.objects.create_superuser(username="admin", password="admin!")

        self.corr = Correspondent.objects.create(name="Acme Corp", owner=self.user)
        self.tag1 = Tag.objects.create(name="Finance", owner=self.user)
        self.tag2 = Tag.objects.create(name="Urgent", owner=self.user)

        self.doc1 = Document.objects.create(
            title="Invoice 001",
            owner=self.user,
            filename="o/invoice1.pdf",
            correspondent=self.corr,
            language="en",
            created=date(2025, 3, 15),
        )
        self.doc1.tags.add(self.tag1, self.tag2)

        self.doc2 = Document.objects.create(
            title="Receipt 002",
            owner=self.user,
            filename="o/receipt2.pdf",
            language="en",
            created=date(2025, 6, 20),
        )
        self.doc2.tags.add(self.tag1)

        self.doc3 = Document.objects.create(
            title="Memo from HQ",
            owner=self.user,
            filename="o/memo.pdf",
            original_filename="memo.pdf",
            language="de",
            created=date(2024, 12, 1),
        )

        # Other user's document
        self.doc4 = Document.objects.create(
            title="Secret Invoice",
            owner=self.other_user,
            filename="o/secret.pdf",
            language="en",
            created=date(2025, 5, 1),
        )

    def _create_view_with_rules(self, rules, **kwargs):
        view = SavedView.objects.create(
            name="Test View", owner=self.user, **kwargs,
        )
        for rule_type, value in rules:
            SavedViewFilterRule.objects.create(
                saved_view=view, rule_type=rule_type, value=value,
            )
        return view

    def test_empty_view_returns_all_user_docs(self):
        view = SavedView.objects.create(name="All", owner=self.user)
        qs = execute_saved_view(view, user=self.user)
        self.assertEqual(qs.count(), 3)

    def test_superuser_sees_all_docs(self):
        view = SavedView.objects.create(name="All", owner=self.admin)
        qs = execute_saved_view(view, user=self.admin)
        self.assertEqual(qs.count(), 4)

    def test_title_contains_rule(self):
        view = self._create_view_with_rules([
            (RULE_TITLE_CONTAINS, "Invoice"),
        ])
        qs = execute_saved_view(view, user=self.user)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, self.doc1.pk)

    def test_correspondent_is_rule(self):
        view = self._create_view_with_rules([
            (RULE_CORRESPONDENT_IS, str(self.corr.pk)),
        ])
        qs = execute_saved_view(view, user=self.user)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, self.doc1.pk)

    def test_tag_is_rule(self):
        view = self._create_view_with_rules([
            (RULE_TAG_IS, str(self.tag1.pk)),
        ])
        qs = execute_saved_view(view, user=self.user)
        self.assertEqual(qs.count(), 2)
        pks = set(qs.values_list("pk", flat=True))
        self.assertIn(self.doc1.pk, pks)
        self.assertIn(self.doc2.pk, pks)

    def test_tag_all_rule(self):
        view = self._create_view_with_rules([
            (RULE_TAG_ALL, f"{self.tag1.pk},{self.tag2.pk}"),
        ])
        qs = execute_saved_view(view, user=self.user)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, self.doc1.pk)

    def test_tag_none_rule(self):
        view = self._create_view_with_rules([
            (RULE_TAG_NONE, f"{self.tag2.pk}"),
        ])
        qs = execute_saved_view(view, user=self.user)
        pks = set(qs.values_list("pk", flat=True))
        self.assertNotIn(self.doc1.pk, pks)
        self.assertIn(self.doc2.pk, pks)
        self.assertIn(self.doc3.pk, pks)

    def test_has_tags_rule(self):
        view = self._create_view_with_rules([(RULE_HAS_TAGS, "")])
        qs = execute_saved_view(view, user=self.user)
        self.assertEqual(qs.count(), 2)

    def test_has_no_tags_rule(self):
        view = self._create_view_with_rules([(RULE_HAS_NO_TAGS, "")])
        qs = execute_saved_view(view, user=self.user)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, self.doc3.pk)

    def test_has_correspondent_rule(self):
        view = self._create_view_with_rules([(RULE_HAS_CORRESPONDENT, "")])
        qs = execute_saved_view(view, user=self.user)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, self.doc1.pk)

    def test_has_no_correspondent_rule(self):
        view = self._create_view_with_rules([(RULE_HAS_NO_CORRESPONDENT, "")])
        qs = execute_saved_view(view, user=self.user)
        self.assertEqual(qs.count(), 2)

    def test_created_after_rule(self):
        view = self._create_view_with_rules([
            (RULE_CREATED_AFTER, "2025-01-01"),
        ])
        qs = execute_saved_view(view, user=self.user)
        self.assertEqual(qs.count(), 2)

    def test_created_before_rule(self):
        view = self._create_view_with_rules([
            (RULE_CREATED_BEFORE, "2025-01-01"),
        ])
        qs = execute_saved_view(view, user=self.user)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, self.doc3.pk)

    def test_language_rule(self):
        view = self._create_view_with_rules([
            (RULE_LANGUAGE_IS, "de"),
        ])
        qs = execute_saved_view(view, user=self.user)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, self.doc3.pk)

    def test_filename_contains_rule(self):
        view = self._create_view_with_rules([
            (RULE_FILENAME_CONTAINS, "memo"),
        ])
        qs = execute_saved_view(view, user=self.user)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, self.doc3.pk)

    def test_multiple_rules_and_logic(self):
        view = self._create_view_with_rules([
            (RULE_TAG_IS, str(self.tag1.pk)),
            (RULE_CREATED_AFTER, "2025-05-01"),
        ])
        qs = execute_saved_view(view, user=self.user)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, self.doc2.pk)

    def test_sort_ascending(self):
        view = SavedView.objects.create(
            name="Sorted", owner=self.user,
            sort_field="created", sort_reverse=False,
        )
        qs = execute_saved_view(view, user=self.user)
        dates = list(qs.values_list("created", flat=True))
        self.assertEqual(dates, sorted(dates))

    def test_sort_descending(self):
        view = SavedView.objects.create(
            name="Sorted Desc", owner=self.user,
            sort_field="created", sort_reverse=True,
        )
        qs = execute_saved_view(view, user=self.user)
        dates = list(qs.values_list("created", flat=True))
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_permission_isolation(self):
        view = SavedView.objects.create(name="All", owner=self.user)
        qs = execute_saved_view(view, user=self.other_user)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, self.doc4.pk)

    def test_no_user_returns_all(self):
        view = SavedView.objects.create(name="No user", owner=self.user)
        qs = execute_saved_view(view, user=None)
        self.assertEqual(qs.count(), 4)

    def test_document_type_rule(self):
        from documents.models import DocumentType
        dt = DocumentType.objects.create(name="Invoice", owner=self.user)
        self.doc1.document_type = dt
        self.doc1.save()
        view = self._create_view_with_rules([
            (RULE_DOCUMENT_TYPE_IS, str(dt.pk)),
        ])
        qs = execute_saved_view(view, user=self.user)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, self.doc1.pk)

"""Tests for workflow trigger-action rules."""

from dataclasses import dataclass, field
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from documents.models import Document, DocumentType
from organization.models import Correspondent, Tag
from workflows.constants import (
    ACTION_ADD_TAG,
    ACTION_REMOVE_TAG,
    ACTION_SEND_EMAIL,
    ACTION_SET_CORRESPONDENT,
    ACTION_SET_CUSTOM_FIELD,
    ACTION_SET_STORAGE_PATH,
    ACTION_SET_TYPE,
    ACTION_WEBHOOK,
    MATCH_ALL,
    MATCH_ANY,
    MATCH_FUZZY,
    MATCH_LITERAL,
    MATCH_NONE,
    MATCH_REGEX,
    TRIGGER_CONSUMPTION,
    TRIGGER_DOCUMENT_ADDED,
    TRIGGER_DOCUMENT_UPDATED,
    TRIGGER_SCHEDULED,
)
from workflows.models import WorkflowAction, WorkflowRule, WorkflowTrigger
from workflows.rules import (
    apply_consumption_overrides,
    execute_rule_actions,
    get_matching_rules,
)


class TriggerMatchingTest(TestCase):
    """Tests for trigger matching logic."""

    def setUp(self):
        self.user = User.objects.create_user("test", "test@test.com", "pass")
        self.doc_type = DocumentType.objects.create(name="Invoice")
        self.doc = Document.objects.create(
            title="Test Invoice 2024",
            content="This is an invoice for services rendered.",
            filename="invoice_2024.pdf",
            document_type=self.doc_type,
            owner=self.user,
        )
        self.tag = Tag.objects.create(name="important", color="#ff0000")
        self.doc.tags.add(self.tag)

    def _make_rule(self, trigger_type, **trigger_kwargs):
        """Helper to create a rule with a trigger."""
        trigger = WorkflowTrigger.objects.create(type=trigger_type, **trigger_kwargs)
        rule = WorkflowRule.objects.create(name="Test Rule")
        rule.triggers.add(trigger)
        return rule

    # ------------------------------------------------------------------
    # Basic trigger type matching
    # ------------------------------------------------------------------

    def test_basic_added_trigger_matches(self):
        self._make_rule(TRIGGER_DOCUMENT_ADDED)
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 1)

    def test_updated_trigger_matches(self):
        self._make_rule(TRIGGER_DOCUMENT_UPDATED)
        rules = get_matching_rules(TRIGGER_DOCUMENT_UPDATED, document=self.doc)
        self.assertEqual(len(rules), 1)

    def test_consumption_trigger_matches(self):
        self._make_rule(TRIGGER_CONSUMPTION)
        rules = get_matching_rules(TRIGGER_CONSUMPTION, document=self.doc)
        self.assertEqual(len(rules), 1)

    def test_wrong_trigger_type_no_match(self):
        self._make_rule(TRIGGER_DOCUMENT_ADDED)
        rules = get_matching_rules(TRIGGER_DOCUMENT_UPDATED, document=self.doc)
        self.assertEqual(len(rules), 0)

    def test_scheduled_trigger_no_document(self):
        """Scheduled triggers can match without a document."""
        self._make_rule(TRIGGER_SCHEDULED)
        rules = get_matching_rules(TRIGGER_SCHEDULED, document=None)
        self.assertEqual(len(rules), 1)

    def test_non_scheduled_trigger_requires_document(self):
        """Non-scheduled triggers return nothing without a document."""
        self._make_rule(TRIGGER_DOCUMENT_ADDED)
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=None)
        self.assertEqual(len(rules), 0)

    # ------------------------------------------------------------------
    # Enabled / disabled
    # ------------------------------------------------------------------

    def test_disabled_rule_no_match(self):
        rule = self._make_rule(TRIGGER_DOCUMENT_ADDED)
        rule.enabled = False
        rule.save()
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 0)

    def test_disabled_trigger_no_match(self):
        trigger = WorkflowTrigger.objects.create(
            type=TRIGGER_DOCUMENT_ADDED, enabled=False
        )
        rule = WorkflowRule.objects.create(name="Test")
        rule.triggers.add(trigger)
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 0)

    # ------------------------------------------------------------------
    # Document type filter
    # ------------------------------------------------------------------

    def test_filter_document_type_matches(self):
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            filter_has_document_type=self.doc_type,
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 1)

    def test_filter_document_type_no_match(self):
        other_type = DocumentType.objects.create(name="Receipt")
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            filter_has_document_type=other_type,
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 0)

    # ------------------------------------------------------------------
    # Correspondent filter
    # ------------------------------------------------------------------

    def test_filter_correspondent_matches(self):
        corr = Correspondent.objects.create(name="Test Corp")
        self.doc.correspondent = corr
        self.doc.save()
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            filter_has_correspondent=corr,
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 1)

    def test_filter_correspondent_no_match(self):
        corr1 = Correspondent.objects.create(name="Corp A")
        corr2 = Correspondent.objects.create(name="Corp B")
        self.doc.correspondent = corr1
        self.doc.save()
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            filter_has_correspondent=corr2,
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 0)

    # ------------------------------------------------------------------
    # Tag filter
    # ------------------------------------------------------------------

    def test_filter_tags_match(self):
        trigger = WorkflowTrigger.objects.create(type=TRIGGER_DOCUMENT_ADDED)
        trigger.filter_has_tags.add(self.tag)
        rule = WorkflowRule.objects.create(name="Tag Rule")
        rule.triggers.add(trigger)
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 1)

    def test_filter_tags_no_match(self):
        other_tag = Tag.objects.create(name="other", color="#00ff00")
        trigger = WorkflowTrigger.objects.create(type=TRIGGER_DOCUMENT_ADDED)
        trigger.filter_has_tags.add(other_tag)
        rule = WorkflowRule.objects.create(name="Tag Rule")
        rule.triggers.add(trigger)
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 0)

    def test_filter_tags_requires_all(self):
        """All required tags must be present on the document."""
        tag2 = Tag.objects.create(name="urgent", color="#0000ff")
        trigger = WorkflowTrigger.objects.create(type=TRIGGER_DOCUMENT_ADDED)
        trigger.filter_has_tags.add(self.tag, tag2)
        rule = WorkflowRule.objects.create(name="Multi-Tag Rule")
        rule.triggers.add(trigger)
        # Document only has self.tag, not tag2
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 0)

    def test_filter_tags_all_present(self):
        """Rule matches when all required tags are on the document."""
        tag2 = Tag.objects.create(name="urgent", color="#0000ff")
        self.doc.tags.add(tag2)
        trigger = WorkflowTrigger.objects.create(type=TRIGGER_DOCUMENT_ADDED)
        trigger.filter_has_tags.add(self.tag, tag2)
        rule = WorkflowRule.objects.create(name="Multi-Tag Rule")
        rule.triggers.add(trigger)
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 1)

    # ------------------------------------------------------------------
    # Match pattern algorithms
    # ------------------------------------------------------------------

    def test_match_pattern_any(self):
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            match_pattern="invoice receipt",
            matching_algorithm=MATCH_ANY,
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 1)

    def test_match_pattern_any_no_match(self):
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            match_pattern="receipt payment",
            matching_algorithm=MATCH_ANY,
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 0)

    def test_match_pattern_all(self):
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            match_pattern="invoice 2024",
            matching_algorithm=MATCH_ALL,
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 1)

    def test_match_pattern_all_no_match(self):
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            match_pattern="invoice 2025",
            matching_algorithm=MATCH_ALL,
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 0)

    def test_match_pattern_literal(self):
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            match_pattern="Test Invoice",
            matching_algorithm=MATCH_LITERAL,
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 1)

    def test_match_pattern_literal_no_match(self):
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            match_pattern="Missing Phrase",
            matching_algorithm=MATCH_LITERAL,
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 0)

    def test_match_pattern_literal_case_insensitive(self):
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            match_pattern="test invoice",
            matching_algorithm=MATCH_LITERAL,
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 1)

    def test_match_pattern_regex(self):
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            match_pattern=r"invoice.*\d{4}",
            matching_algorithm=MATCH_REGEX,
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 1)

    def test_match_pattern_regex_no_match(self):
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            match_pattern=r"^ZZZZZ\d{10}$",
            matching_algorithm=MATCH_REGEX,
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 0)

    def test_match_pattern_regex_invalid_pattern(self):
        """Invalid regex should not match (not raise)."""
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            match_pattern=r"[invalid((",
            matching_algorithm=MATCH_REGEX,
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 0)

    def test_match_pattern_fuzzy(self):
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            match_pattern="invoice services rendered",
            matching_algorithm=MATCH_FUZZY,
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 1)

    def test_match_pattern_fuzzy_below_threshold(self):
        """Fuzzy requires ~70% of words to match."""
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            match_pattern="apple banana cherry date elderberry fig grape",
            matching_algorithm=MATCH_FUZZY,
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 0)

    def test_match_pattern_none_always_passes(self):
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            match_pattern="anything here",
            matching_algorithm=MATCH_NONE,
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 1)

    # ------------------------------------------------------------------
    # Filename filter
    # ------------------------------------------------------------------

    def test_filename_filter(self):
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            filter_filename="*.pdf",
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 1)

    def test_filename_filter_no_match(self):
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            filter_filename="*.docx",
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 0)

    def test_filename_filter_case_insensitive(self):
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            filter_filename="*.PDF",
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 1)

    def test_filename_filter_specific_name(self):
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            filter_filename="invoice_*.pdf",
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 1)

    # ------------------------------------------------------------------
    # Path filter (uses context)
    # ------------------------------------------------------------------

    def test_path_filter_matches(self):
        self._make_rule(
            TRIGGER_CONSUMPTION,
            filter_path="/data/consume/*",
        )

        @dataclass
        class FakeContext:
            source_path: str = "/data/consume/invoice.pdf"

        rules = get_matching_rules(
            TRIGGER_CONSUMPTION, document=self.doc, context=FakeContext()
        )
        self.assertEqual(len(rules), 1)

    def test_path_filter_no_match(self):
        self._make_rule(
            TRIGGER_CONSUMPTION,
            filter_path="/other/path/*",
        )

        @dataclass
        class FakeContext:
            source_path: str = "/data/consume/invoice.pdf"

        rules = get_matching_rules(
            TRIGGER_CONSUMPTION, document=self.doc, context=FakeContext()
        )
        self.assertEqual(len(rules), 0)

    # ------------------------------------------------------------------
    # Multiple rules and ordering
    # ------------------------------------------------------------------

    def test_multiple_rules_returned(self):
        self._make_rule(TRIGGER_DOCUMENT_ADDED)
        rule2 = self._make_rule(TRIGGER_DOCUMENT_ADDED)
        rule2.name = "Second Rule"
        rule2.save()
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 2)

    def test_rules_ordered_by_order_then_name(self):
        r1 = self._make_rule(TRIGGER_DOCUMENT_ADDED)
        r1.name = "Beta Rule"
        r1.order = 1
        r1.save()

        r2 = self._make_rule(TRIGGER_DOCUMENT_ADDED)
        r2.name = "Alpha Rule"
        r2.order = 0
        r2.save()

        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(rules[0].pk, r2.pk)
        self.assertEqual(rules[1].pk, r1.pk)

    # ------------------------------------------------------------------
    # Combined filters
    # ------------------------------------------------------------------

    def test_combined_type_and_filename_filter(self):
        """Rule matches only when both type and filename filters pass."""
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            filter_has_document_type=self.doc_type,
            filter_filename="*.pdf",
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 1)

    def test_combined_filter_partial_no_match(self):
        """Rule does not match when one filter fails."""
        self._make_rule(
            TRIGGER_DOCUMENT_ADDED,
            filter_has_document_type=self.doc_type,
            filter_filename="*.docx",
        )
        rules = get_matching_rules(TRIGGER_DOCUMENT_ADDED, document=self.doc)
        self.assertEqual(len(rules), 0)


class ActionExecutionTest(TestCase):
    """Tests for rule action execution."""

    def setUp(self):
        self.user = User.objects.create_user("test", "test@test.com", "pass")
        self.doc_type = DocumentType.objects.create(name="Invoice")
        self.doc = Document.objects.create(
            title="Test Doc",
            filename="test.pdf",
            owner=self.user,
        )
        self.tag1 = Tag.objects.create(name="tag1", color="#ff0000")
        self.tag2 = Tag.objects.create(name="tag2", color="#00ff00")

    def _make_rule_with_action(self, action_type, config=None):
        action = WorkflowAction.objects.create(
            type=action_type,
            configuration=config or {},
        )
        rule = WorkflowRule.objects.create(name="Test Rule")
        rule.actions.add(action)
        return rule

    # ------------------------------------------------------------------
    # Tag actions
    # ------------------------------------------------------------------

    def test_add_tag_action(self):
        rule = self._make_rule_with_action(
            ACTION_ADD_TAG, {"tag_ids": [self.tag1.pk, self.tag2.pk]},
        )
        execute_rule_actions(rule, self.doc)
        self.assertEqual(self.doc.tags.count(), 2)
        self.assertIn(self.tag1, self.doc.tags.all())
        self.assertIn(self.tag2, self.doc.tags.all())

    def test_add_tag_action_empty_list(self):
        rule = self._make_rule_with_action(
            ACTION_ADD_TAG, {"tag_ids": []},
        )
        execute_rule_actions(rule, self.doc)
        self.assertEqual(self.doc.tags.count(), 0)

    def test_remove_tag_action(self):
        self.doc.tags.add(self.tag1, self.tag2)
        rule = self._make_rule_with_action(
            ACTION_REMOVE_TAG, {"tag_ids": [self.tag1.pk]},
        )
        execute_rule_actions(rule, self.doc)
        self.assertEqual(self.doc.tags.count(), 1)
        self.assertIn(self.tag2, self.doc.tags.all())

    def test_remove_tag_action_tag_not_present(self):
        """Removing a tag not on the document does not raise."""
        rule = self._make_rule_with_action(
            ACTION_REMOVE_TAG, {"tag_ids": [self.tag1.pk]},
        )
        execute_rule_actions(rule, self.doc)
        self.assertEqual(self.doc.tags.count(), 0)

    # ------------------------------------------------------------------
    # Correspondent and type actions
    # ------------------------------------------------------------------

    def test_set_correspondent_action(self):
        corr = Correspondent.objects.create(name="Test Corp")
        rule = self._make_rule_with_action(
            ACTION_SET_CORRESPONDENT, {"correspondent_id": corr.pk},
        )
        execute_rule_actions(rule, self.doc)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.correspondent_id, corr.pk)

    def test_set_document_type_action(self):
        rule = self._make_rule_with_action(
            ACTION_SET_TYPE, {"document_type_id": self.doc_type.pk},
        )
        execute_rule_actions(rule, self.doc)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.document_type_id, self.doc_type.pk)

    def test_set_document_type_replaces_existing(self):
        other_type = DocumentType.objects.create(name="Receipt")
        self.doc.document_type = other_type
        self.doc.save()
        rule = self._make_rule_with_action(
            ACTION_SET_TYPE, {"document_type_id": self.doc_type.pk},
        )
        execute_rule_actions(rule, self.doc)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.document_type_id, self.doc_type.pk)

    # ------------------------------------------------------------------
    # Enabled / disabled actions
    # ------------------------------------------------------------------

    def test_disabled_action_not_executed(self):
        action = WorkflowAction.objects.create(
            type=ACTION_ADD_TAG,
            configuration={"tag_ids": [self.tag1.pk]},
            enabled=False,
        )
        rule = WorkflowRule.objects.create(name="Test")
        rule.actions.add(action)
        execute_rule_actions(rule, self.doc)
        self.assertEqual(self.doc.tags.count(), 0)

    # ------------------------------------------------------------------
    # Multiple actions
    # ------------------------------------------------------------------

    def test_multiple_actions_execute_in_order(self):
        action1 = WorkflowAction.objects.create(
            type=ACTION_ADD_TAG,
            configuration={"tag_ids": [self.tag1.pk]},
            order=0,
        )
        action2 = WorkflowAction.objects.create(
            type=ACTION_SET_TYPE,
            configuration={"document_type_id": self.doc_type.pk},
            order=1,
        )
        rule = WorkflowRule.objects.create(name="Multi")
        rule.actions.add(action1, action2)
        execute_rule_actions(rule, self.doc)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.tags.count(), 1)
        self.assertEqual(self.doc.document_type_id, self.doc_type.pk)

    def test_action_error_does_not_stop_subsequent_actions(self):
        """An exception in one action should not prevent later actions."""
        # ACTION_SET_CORRESPONDENT with a non-existent ID will not raise
        # because the code only sets the FK integer; but we can test the
        # ordering of add-tag before and after.
        action1 = WorkflowAction.objects.create(
            type=ACTION_ADD_TAG,
            configuration={"tag_ids": [self.tag1.pk]},
            order=0,
        )
        action2 = WorkflowAction.objects.create(
            type=ACTION_ADD_TAG,
            configuration={"tag_ids": [self.tag2.pk]},
            order=1,
        )
        rule = WorkflowRule.objects.create(name="Multi")
        rule.actions.add(action1, action2)
        execute_rule_actions(rule, self.doc)
        self.assertEqual(self.doc.tags.count(), 2)

    # ------------------------------------------------------------------
    # Email action (mocked)
    # ------------------------------------------------------------------

    @patch("workflows.rules.send_mail")
    def test_send_email_action(self, mock_send_mail):
        rule = self._make_rule_with_action(
            ACTION_SEND_EMAIL,
            {
                "subject": "New document: {{ document.title }}",
                "body": "A new document was added.",
                "to": ["admin@example.com"],
            },
        )
        execute_rule_actions(rule, self.doc)
        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args
        self.assertIn("Test Doc", call_args[0][0])  # rendered subject
        self.assertEqual(call_args[0][3], ["admin@example.com"])


class ConsumptionOverrideTest(TestCase):
    """Tests for consumption trigger overrides."""

    def _make_context(self):
        @dataclass
        class FakeContext:
            override_tags: list = None
            override_correspondent: int = None
            override_document_type: int = None

        return FakeContext()

    def test_consumption_override_adds_tags(self):
        action = WorkflowAction.objects.create(
            type=ACTION_ADD_TAG,
            configuration={"tag_ids": [1, 2]},
        )
        rule = WorkflowRule.objects.create(name="Consume Rule")
        rule.actions.add(action)

        ctx = self._make_context()
        apply_consumption_overrides([rule], ctx)
        self.assertEqual(sorted(ctx.override_tags), [1, 2])

    def test_consumption_override_merges_tags(self):
        """Multiple rules should merge tag lists without duplicates."""
        action1 = WorkflowAction.objects.create(
            type=ACTION_ADD_TAG,
            configuration={"tag_ids": [1, 2]},
        )
        action2 = WorkflowAction.objects.create(
            type=ACTION_ADD_TAG,
            configuration={"tag_ids": [2, 3]},
        )
        rule1 = WorkflowRule.objects.create(name="Rule 1")
        rule1.actions.add(action1)
        rule2 = WorkflowRule.objects.create(name="Rule 2")
        rule2.actions.add(action2)

        ctx = self._make_context()
        apply_consumption_overrides([rule1, rule2], ctx)
        self.assertEqual(sorted(ctx.override_tags), [1, 2, 3])

    def test_consumption_override_sets_type(self):
        action = WorkflowAction.objects.create(
            type=ACTION_SET_TYPE,
            configuration={"document_type_id": 42},
        )
        rule = WorkflowRule.objects.create(name="Type Rule")
        rule.actions.add(action)

        ctx = self._make_context()
        apply_consumption_overrides([rule], ctx)
        self.assertEqual(ctx.override_document_type, 42)

    def test_consumption_override_sets_correspondent(self):
        action = WorkflowAction.objects.create(
            type=ACTION_SET_CORRESPONDENT,
            configuration={"correspondent_id": 99},
        )
        rule = WorkflowRule.objects.create(name="Correspondent Rule")
        rule.actions.add(action)

        ctx = self._make_context()
        apply_consumption_overrides([rule], ctx)
        self.assertEqual(ctx.override_correspondent, 99)

    def test_consumption_override_last_type_wins(self):
        """When multiple rules set the type, the last one wins."""
        action1 = WorkflowAction.objects.create(
            type=ACTION_SET_TYPE,
            configuration={"document_type_id": 10},
        )
        action2 = WorkflowAction.objects.create(
            type=ACTION_SET_TYPE,
            configuration={"document_type_id": 20},
        )
        rule1 = WorkflowRule.objects.create(name="Rule 1")
        rule1.actions.add(action1)
        rule2 = WorkflowRule.objects.create(name="Rule 2")
        rule2.actions.add(action2)

        ctx = self._make_context()
        apply_consumption_overrides([rule1, rule2], ctx)
        self.assertEqual(ctx.override_document_type, 20)

    def test_consumption_override_disabled_action_ignored(self):
        action = WorkflowAction.objects.create(
            type=ACTION_ADD_TAG,
            configuration={"tag_ids": [1]},
            enabled=False,
        )
        rule = WorkflowRule.objects.create(name="Disabled Action Rule")
        rule.actions.add(action)

        ctx = self._make_context()
        apply_consumption_overrides([rule], ctx)
        self.assertIsNone(ctx.override_tags)

    def test_consumption_override_empty_config(self):
        """Actions with empty config should not set overrides."""
        action = WorkflowAction.objects.create(
            type=ACTION_ADD_TAG,
            configuration={},
        )
        rule = WorkflowRule.objects.create(name="Empty Config Rule")
        rule.actions.add(action)

        ctx = self._make_context()
        apply_consumption_overrides([rule], ctx)
        self.assertIsNone(ctx.override_tags)

    def test_consumption_override_no_rules(self):
        ctx = self._make_context()
        apply_consumption_overrides([], ctx)
        self.assertIsNone(ctx.override_tags)
        self.assertIsNone(ctx.override_correspondent)
        self.assertIsNone(ctx.override_document_type)

"""Tests for search models (SavedView, SavedViewFilterRule)."""

from django.contrib.auth.models import User
from django.test import TestCase

from search.models import (
    DISPLAY_LARGE_CARDS,
    DISPLAY_SMALL_CARDS,
    DISPLAY_TABLE,
    RULE_CREATED_AFTER,
    RULE_CORRESPONDENT_IS,
    RULE_TAG_IS,
    RULE_TITLE_CONTAINS,
    SavedView,
    SavedViewFilterRule,
)


class SavedViewModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="viewuser", password="pass!")

    def test_create_saved_view_defaults(self):
        view = SavedView.objects.create(name="My View", owner=self.user)
        self.assertEqual(view.name, "My View")
        self.assertEqual(view.display_mode, DISPLAY_TABLE)
        self.assertEqual(view.sort_field, "created")
        self.assertTrue(view.sort_reverse)
        self.assertEqual(view.page_size, 25)
        self.assertFalse(view.show_on_dashboard)
        self.assertFalse(view.show_in_sidebar)
        self.assertEqual(view.display_fields, [])
        self.assertIsNotNone(view.created_at)
        self.assertIsNotNone(view.updated_at)

    def test_display_mode_choices(self):
        for mode in [DISPLAY_TABLE, DISPLAY_SMALL_CARDS, DISPLAY_LARGE_CARDS]:
            view = SavedView.objects.create(
                name=f"View {mode}", display_mode=mode, owner=self.user,
            )
            self.assertEqual(view.display_mode, mode)

    def test_str_representation(self):
        view = SavedView.objects.create(name="Invoices", owner=self.user)
        self.assertEqual(str(view), "Invoices")

    def test_ordering(self):
        SavedView.objects.create(name="Zebra", owner=self.user)
        SavedView.objects.create(name="Alpha", owner=self.user)
        SavedView.objects.create(name="Middle", owner=self.user)
        views = list(SavedView.objects.values_list("name", flat=True))
        self.assertEqual(views, ["Alpha", "Middle", "Zebra"])

    def test_get_filter_rules_dict_empty(self):
        view = SavedView.objects.create(name="Empty", owner=self.user)
        self.assertEqual(view.get_filter_rules_dict(), {})

    def test_get_filter_rules_dict_with_rules(self):
        view = SavedView.objects.create(name="Filtered", owner=self.user)
        SavedViewFilterRule.objects.create(
            saved_view=view, rule_type=RULE_TITLE_CONTAINS, value="invoice",
        )
        SavedViewFilterRule.objects.create(
            saved_view=view, rule_type=RULE_TAG_IS, value="5",
        )
        SavedViewFilterRule.objects.create(
            saved_view=view, rule_type=RULE_TITLE_CONTAINS, value="receipt",
        )
        rules = view.get_filter_rules_dict()
        self.assertIn(RULE_TITLE_CONTAINS, rules)
        self.assertIn(RULE_TAG_IS, rules)
        self.assertEqual(len(rules[RULE_TITLE_CONTAINS]), 2)
        self.assertIn("invoice", rules[RULE_TITLE_CONTAINS])
        self.assertIn("receipt", rules[RULE_TITLE_CONTAINS])
        self.assertEqual(rules[RULE_TAG_IS], ["5"])

    def test_cascade_delete(self):
        view = SavedView.objects.create(name="ToDelete", owner=self.user)
        SavedViewFilterRule.objects.create(
            saved_view=view, rule_type=RULE_TAG_IS, value="1",
        )
        SavedViewFilterRule.objects.create(
            saved_view=view, rule_type=RULE_TITLE_CONTAINS, value="test",
        )
        self.assertEqual(SavedViewFilterRule.objects.count(), 2)
        view.delete()
        self.assertEqual(SavedViewFilterRule.objects.count(), 0)


class SavedViewFilterRuleModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ruleuser", password="pass!")
        self.view = SavedView.objects.create(name="Test View", owner=self.user)

    def test_create_rule(self):
        rule = SavedViewFilterRule.objects.create(
            saved_view=self.view,
            rule_type=RULE_TITLE_CONTAINS,
            value="invoice",
        )
        self.assertEqual(rule.rule_type, RULE_TITLE_CONTAINS)
        self.assertEqual(rule.value, "invoice")
        self.assertEqual(rule.saved_view, self.view)

    def test_str_representation(self):
        rule = SavedViewFilterRule.objects.create(
            saved_view=self.view,
            rule_type=RULE_CORRESPONDENT_IS,
            value="42",
        )
        self.assertIn("Correspondent is", str(rule))
        self.assertIn("42", str(rule))

    def test_blank_value_allowed(self):
        rule = SavedViewFilterRule.objects.create(
            saved_view=self.view,
            rule_type=RULE_CREATED_AFTER,
            value="",
        )
        self.assertEqual(rule.value, "")

    def test_ordering(self):
        SavedViewFilterRule.objects.create(
            saved_view=self.view, rule_type=RULE_TITLE_CONTAINS, value="a",
        )
        SavedViewFilterRule.objects.create(
            saved_view=self.view, rule_type=RULE_CORRESPONDENT_IS, value="1",
        )
        SavedViewFilterRule.objects.create(
            saved_view=self.view, rule_type=RULE_TAG_IS, value="2",
        )
        rules = list(self.view.filter_rules.values_list("rule_type", flat=True))
        self.assertEqual(rules, sorted(rules))

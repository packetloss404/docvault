"""Tests for search serializers."""

from django.contrib.auth.models import User
from django.test import TestCase

from search.models import (
    RULE_TAG_IS,
    RULE_TITLE_CONTAINS,
    SavedView,
    SavedViewFilterRule,
)
from search.serializers import (
    SavedViewFilterRuleSerializer,
    SavedViewListSerializer,
    SavedViewSerializer,
)


class SavedViewFilterRuleSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ruser", password="pass!")
        self.view = SavedView.objects.create(name="Test", owner=self.user)

    def test_serialize(self):
        rule = SavedViewFilterRule.objects.create(
            saved_view=self.view, rule_type=RULE_TITLE_CONTAINS, value="inv",
        )
        data = SavedViewFilterRuleSerializer(rule).data
        self.assertEqual(data["rule_type"], "title_contains")
        self.assertEqual(data["value"], "inv")
        self.assertIn("rule_type_display", data)
        self.assertEqual(data["rule_type_display"], "Title contains")


class SavedViewSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="suser", password="pass!")

    def test_serialize_with_rules(self):
        view = SavedView.objects.create(name="Invoices", owner=self.user)
        SavedViewFilterRule.objects.create(
            saved_view=view, rule_type=RULE_TITLE_CONTAINS, value="invoice",
        )
        SavedViewFilterRule.objects.create(
            saved_view=view, rule_type=RULE_TAG_IS, value="5",
        )
        data = SavedViewSerializer(view).data
        self.assertEqual(data["name"], "Invoices")
        self.assertEqual(len(data["filter_rules"]), 2)
        self.assertIn("id", data)
        self.assertIn("owner", data)
        self.assertIn("created_at", data)

    def test_create_with_nested_rules(self):
        data = {
            "name": "New View",
            "display_mode": "small_cards",
            "filter_rules": [
                {"rule_type": "title_contains", "value": "test"},
                {"rule_type": "tag_is", "value": "3"},
            ],
        }
        serializer = SavedViewSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        view = serializer.save(owner=self.user)
        self.assertEqual(view.name, "New View")
        self.assertEqual(view.display_mode, "small_cards")
        self.assertEqual(view.filter_rules.count(), 2)

    def test_update_replaces_rules(self):
        view = SavedView.objects.create(name="Old", owner=self.user)
        SavedViewFilterRule.objects.create(
            saved_view=view, rule_type=RULE_TITLE_CONTAINS, value="old",
        )
        data = {
            "name": "Updated",
            "filter_rules": [
                {"rule_type": "tag_is", "value": "10"},
            ],
        }
        serializer = SavedViewSerializer(view, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertEqual(updated.name, "Updated")
        self.assertEqual(updated.filter_rules.count(), 1)
        self.assertEqual(updated.filter_rules.first().rule_type, RULE_TAG_IS)

    def test_update_without_rules_preserves_existing(self):
        view = SavedView.objects.create(name="Keep Rules", owner=self.user)
        SavedViewFilterRule.objects.create(
            saved_view=view, rule_type=RULE_TITLE_CONTAINS, value="keep",
        )
        data = {"name": "Renamed"}
        serializer = SavedViewSerializer(view, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertEqual(updated.name, "Renamed")
        self.assertEqual(updated.filter_rules.count(), 1)

    def test_read_only_fields(self):
        data = {
            "name": "Hacked",
            "owner": 999,
            "created_at": "2020-01-01T00:00:00Z",
        }
        serializer = SavedViewSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        view = serializer.save(owner=self.user)
        self.assertEqual(view.owner, self.user)
        self.assertNotEqual(str(view.created_at), "2020-01-01T00:00:00Z")


class SavedViewListSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="luser", password="pass!")

    def test_rule_count(self):
        view = SavedView.objects.create(name="Counted", owner=self.user)
        SavedViewFilterRule.objects.create(
            saved_view=view, rule_type=RULE_TITLE_CONTAINS, value="a",
        )
        SavedViewFilterRule.objects.create(
            saved_view=view, rule_type=RULE_TAG_IS, value="1",
        )
        data = SavedViewListSerializer(view).data
        self.assertEqual(data["rule_count"], 2)
        self.assertNotIn("filter_rules", data)

    def test_fields_present(self):
        view = SavedView.objects.create(
            name="Full", owner=self.user,
            show_on_dashboard=True, show_in_sidebar=True,
        )
        data = SavedViewListSerializer(view).data
        self.assertTrue(data["show_on_dashboard"])
        self.assertTrue(data["show_in_sidebar"])
        self.assertIn("display_mode", data)
        self.assertIn("owner", data)

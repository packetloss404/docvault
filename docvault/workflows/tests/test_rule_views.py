"""Tests for workflow rule API views."""

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from workflows.constants import (
    ACTION_ADD_TAG,
    ACTION_SET_TYPE,
    MATCH_LITERAL,
    TRIGGER_CONSUMPTION,
    TRIGGER_DOCUMENT_ADDED,
    TRIGGER_DOCUMENT_UPDATED,
)
from workflows.models import WorkflowAction, WorkflowRule, WorkflowTrigger


class WorkflowRuleViewTest(TestCase):
    """Tests for WorkflowRuleViewSet."""

    def setUp(self):
        self.user = User.objects.create_superuser(
            "admin", "admin@test.com", "adminpass"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.rule = WorkflowRule.objects.create(name="Test Rule")

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def test_list_rules(self):
        resp = self.client.get("/api/v1/workflow-rules/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)

    def test_list_rules_multiple(self):
        WorkflowRule.objects.create(name="Second Rule")
        resp = self.client.get("/api/v1/workflow-rules/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 2)

    def test_retrieve_rule(self):
        resp = self.client.get(f"/api/v1/workflow-rules/{self.rule.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["name"], "Test Rule")
        self.assertTrue(resp.data["enabled"])
        self.assertEqual(resp.data["trigger_count"], 0)
        self.assertEqual(resp.data["action_count"], 0)

    def test_create_rule(self):
        resp = self.client.post("/api/v1/workflow-rules/", {
            "name": "New Rule",
            "enabled": True,
            "order": 10,
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["name"], "New Rule")
        self.assertEqual(resp.data["order"], 10)

    def test_create_rule_defaults(self):
        resp = self.client.post(
            "/api/v1/workflow-rules/",
            {"name": "Default Rule"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["enabled"])
        self.assertEqual(resp.data["order"], 0)

    def test_update_rule(self):
        resp = self.client.patch(
            f"/api/v1/workflow-rules/{self.rule.pk}/",
            {"name": "Updated Rule"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["name"], "Updated Rule")

    def test_update_rule_enabled(self):
        resp = self.client.patch(
            f"/api/v1/workflow-rules/{self.rule.pk}/",
            {"enabled": False},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["enabled"])

    def test_delete_rule(self):
        resp = self.client.delete(f"/api/v1/workflow-rules/{self.rule.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(WorkflowRule.objects.count(), 0)

    def test_delete_nonexistent_rule(self):
        resp = self.client.delete("/api/v1/workflow-rules/99999/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------------------------------------------------------
    # Nested triggers
    # ------------------------------------------------------------------

    def test_create_trigger_for_rule(self):
        resp = self.client.post(
            f"/api/v1/workflow-rules/{self.rule.pk}/triggers/",
            {"type": TRIGGER_DOCUMENT_ADDED, "enabled": True},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.rule.triggers.count(), 1)

    def test_create_trigger_with_filters(self):
        resp = self.client.post(
            f"/api/v1/workflow-rules/{self.rule.pk}/triggers/",
            {
                "type": TRIGGER_DOCUMENT_ADDED,
                "enabled": True,
                "filter_filename": "*.pdf",
                "matching_algorithm": MATCH_LITERAL,
                "match_pattern": "invoice",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        trigger = self.rule.triggers.first()
        self.assertEqual(trigger.filter_filename, "*.pdf")
        self.assertEqual(trigger.matching_algorithm, MATCH_LITERAL)

    def test_list_triggers_for_rule(self):
        trigger = WorkflowTrigger.objects.create(type=TRIGGER_DOCUMENT_ADDED)
        self.rule.triggers.add(trigger)
        resp = self.client.get(
            f"/api/v1/workflow-rules/{self.rule.pk}/triggers/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["type"], TRIGGER_DOCUMENT_ADDED)

    def test_list_triggers_empty(self):
        resp = self.client.get(
            f"/api/v1/workflow-rules/{self.rule.pk}/triggers/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    def test_multiple_triggers_for_rule(self):
        trigger1 = WorkflowTrigger.objects.create(type=TRIGGER_DOCUMENT_ADDED)
        trigger2 = WorkflowTrigger.objects.create(type=TRIGGER_DOCUMENT_UPDATED)
        self.rule.triggers.add(trigger1, trigger2)
        resp = self.client.get(
            f"/api/v1/workflow-rules/{self.rule.pk}/triggers/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

    def test_delete_trigger_from_rule(self):
        trigger = WorkflowTrigger.objects.create(type=TRIGGER_DOCUMENT_ADDED)
        self.rule.triggers.add(trigger)
        resp = self.client.delete(
            f"/api/v1/workflow-rules/{self.rule.pk}/triggers/{trigger.pk}/"
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_update_trigger(self):
        trigger = WorkflowTrigger.objects.create(type=TRIGGER_DOCUMENT_ADDED)
        self.rule.triggers.add(trigger)
        resp = self.client.patch(
            f"/api/v1/workflow-rules/{self.rule.pk}/triggers/{trigger.pk}/",
            {"enabled": False},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["enabled"])

    # ------------------------------------------------------------------
    # Nested actions
    # ------------------------------------------------------------------

    def test_create_action_for_rule(self):
        resp = self.client.post(
            f"/api/v1/workflow-rules/{self.rule.pk}/actions/",
            {
                "type": ACTION_ADD_TAG,
                "configuration": {"tag_ids": [1]},
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.rule.actions.count(), 1)

    def test_create_action_with_order(self):
        resp = self.client.post(
            f"/api/v1/workflow-rules/{self.rule.pk}/actions/",
            {
                "type": ACTION_ADD_TAG,
                "configuration": {"tag_ids": [1]},
                "order": 5,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["order"], 5)

    def test_list_actions_for_rule(self):
        action = WorkflowAction.objects.create(
            type=ACTION_ADD_TAG,
            configuration={"tag_ids": [1]},
        )
        self.rule.actions.add(action)
        resp = self.client.get(
            f"/api/v1/workflow-rules/{self.rule.pk}/actions/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["type"], ACTION_ADD_TAG)

    def test_list_actions_empty(self):
        resp = self.client.get(
            f"/api/v1/workflow-rules/{self.rule.pk}/actions/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    def test_multiple_actions_for_rule(self):
        action1 = WorkflowAction.objects.create(
            type=ACTION_ADD_TAG,
            configuration={"tag_ids": [1]},
            order=0,
        )
        action2 = WorkflowAction.objects.create(
            type=ACTION_SET_TYPE,
            configuration={"document_type_id": 1},
            order=1,
        )
        self.rule.actions.add(action1, action2)
        resp = self.client.get(
            f"/api/v1/workflow-rules/{self.rule.pk}/actions/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

    def test_delete_action_from_rule(self):
        action = WorkflowAction.objects.create(
            type=ACTION_ADD_TAG,
            configuration={"tag_ids": [1]},
        )
        self.rule.actions.add(action)
        resp = self.client.delete(
            f"/api/v1/workflow-rules/{self.rule.pk}/actions/{action.pk}/"
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_update_action(self):
        action = WorkflowAction.objects.create(
            type=ACTION_ADD_TAG,
            configuration={"tag_ids": [1]},
        )
        self.rule.actions.add(action)
        resp = self.client.patch(
            f"/api/v1/workflow-rules/{self.rule.pk}/actions/{action.pk}/",
            {"enabled": False},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["enabled"])

    # ------------------------------------------------------------------
    # Serializer computed fields
    # ------------------------------------------------------------------

    def test_rule_trigger_count(self):
        trigger = WorkflowTrigger.objects.create(type=TRIGGER_DOCUMENT_ADDED)
        self.rule.triggers.add(trigger)
        resp = self.client.get(f"/api/v1/workflow-rules/{self.rule.pk}/")
        self.assertEqual(resp.data["trigger_count"], 1)

    def test_rule_action_count(self):
        action = WorkflowAction.objects.create(
            type=ACTION_ADD_TAG, configuration={}
        )
        self.rule.actions.add(action)
        resp = self.client.get(f"/api/v1/workflow-rules/{self.rule.pk}/")
        self.assertEqual(resp.data["action_count"], 1)

    def test_rule_has_trigger_ids(self):
        trigger = WorkflowTrigger.objects.create(type=TRIGGER_DOCUMENT_ADDED)
        self.rule.triggers.add(trigger)
        resp = self.client.get(f"/api/v1/workflow-rules/{self.rule.pk}/")
        self.assertIn(trigger.pk, resp.data["trigger_ids"])

    def test_rule_has_action_ids(self):
        action = WorkflowAction.objects.create(
            type=ACTION_ADD_TAG, configuration={}
        )
        self.rule.actions.add(action)
        resp = self.client.get(f"/api/v1/workflow-rules/{self.rule.pk}/")
        self.assertIn(action.pk, resp.data["action_ids"])


class WorkflowRuleAuthTest(TestCase):
    """Tests for workflow rule authentication/authorization."""

    def test_rules_require_auth(self):
        client = APIClient()
        resp = client.get("/api/v1/workflow-rules/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rule_triggers_require_auth(self):
        rule = WorkflowRule.objects.create(name="Test")
        client = APIClient()
        resp = client.get(f"/api/v1/workflow-rules/{rule.pk}/triggers/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rule_actions_require_auth(self):
        rule = WorkflowRule.objects.create(name="Test")
        client = APIClient()
        resp = client.get(f"/api/v1/workflow-rules/{rule.pk}/actions/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

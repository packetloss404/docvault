"""Tests for workflow API views."""

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from documents.models import Document, DocumentType
from workflows.engine import launch
from workflows.models import (
    WorkflowInstance,
    WorkflowInstanceLogEntry,
    WorkflowState,
    WorkflowStateAction,
    WorkflowStateEscalation,
    WorkflowTemplate,
    WorkflowTransition,
    WorkflowTransitionField,
)


class WorkflowViewTestBase(TestCase):
    """Base class for workflow view tests."""

    def setUp(self):
        self.user = User.objects.create_superuser(
            "admin", "admin@test.com", "adminpass"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.workflow = WorkflowTemplate.objects.create(label="Test Workflow")
        self.state1 = WorkflowState.objects.create(
            workflow=self.workflow, label="Draft", initial=True, completion=0
        )
        self.state2 = WorkflowState.objects.create(
            workflow=self.workflow, label="Review", completion=50
        )
        self.state3 = WorkflowState.objects.create(
            workflow=self.workflow, label="Approved", final=True, completion=100
        )
        self.transition1 = WorkflowTransition.objects.create(
            workflow=self.workflow,
            label="Submit",
            origin_state=self.state1,
            destination_state=self.state2,
        )
        self.transition2 = WorkflowTransition.objects.create(
            workflow=self.workflow,
            label="Approve",
            origin_state=self.state2,
            destination_state=self.state3,
        )
        self.doc = Document.objects.create(
            title="Test Doc", filename="view_test.pdf", owner=self.user
        )


class WorkflowTemplateViewSetTest(WorkflowViewTestBase):
    """Tests for WorkflowTemplateViewSet."""

    def test_list_templates(self):
        resp = self.client.get("/api/v1/workflow-templates/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)

    def test_create_template(self):
        resp = self.client.post("/api/v1/workflow-templates/", {
            "label": "New Workflow",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["label"], "New Workflow")
        self.assertEqual(resp.data["internal_name"], "new-workflow")

    def test_retrieve_template(self):
        resp = self.client.get(f"/api/v1/workflow-templates/{self.workflow.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["label"], "Test Workflow")
        self.assertEqual(resp.data["state_count"], 3)
        self.assertEqual(resp.data["transition_count"], 2)

    def test_update_template(self):
        resp = self.client.patch(
            f"/api/v1/workflow-templates/{self.workflow.pk}/",
            {"label": "Updated Workflow", "auto_launch": True},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["label"], "Updated Workflow")
        self.assertTrue(resp.data["auto_launch"])

    def test_delete_template(self):
        resp = self.client.delete(
            f"/api/v1/workflow-templates/{self.workflow.pk}/"
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(WorkflowTemplate.objects.count(), 0)


class NestedStateViewTest(WorkflowViewTestBase):
    """Tests for nested state endpoints."""

    def test_list_states(self):
        resp = self.client.get(
            f"/api/v1/workflow-templates/{self.workflow.pk}/states/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 3)

    def test_create_state(self):
        resp = self.client.post(
            f"/api/v1/workflow-templates/{self.workflow.pk}/states/",
            {"label": "Rejected", "completion": 0},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["label"], "Rejected")

    def test_delete_state(self):
        resp = self.client.delete(
            f"/api/v1/workflow-templates/{self.workflow.pk}/states/{self.state2.pk}/"
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)


class NestedTransitionViewTest(WorkflowViewTestBase):
    """Tests for nested transition endpoints."""

    def test_list_transitions(self):
        resp = self.client.get(
            f"/api/v1/workflow-templates/{self.workflow.pk}/transitions/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

    def test_create_transition(self):
        resp = self.client.post(
            f"/api/v1/workflow-templates/{self.workflow.pk}/transitions/",
            {
                "label": "Reject",
                "origin_state": self.state2.pk,
                "destination_state": self.state1.pk,
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_transition_includes_state_labels(self):
        resp = self.client.get(
            f"/api/v1/workflow-templates/{self.workflow.pk}/transitions/"
        )
        first = resp.data[0]
        self.assertIn("origin_state_label", first)
        self.assertIn("destination_state_label", first)


class NestedFieldViewTest(WorkflowViewTestBase):
    """Tests for nested transition field endpoints."""

    def test_list_fields(self):
        WorkflowTransitionField.objects.create(
            transition=self.transition1,
            name="reason",
            label="Reason",
        )
        resp = self.client.get(
            f"/api/v1/workflow-templates/{self.workflow.pk}"
            f"/transitions/{self.transition1.pk}/fields/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_create_field(self):
        resp = self.client.post(
            f"/api/v1/workflow-templates/{self.workflow.pk}"
            f"/transitions/{self.transition1.pk}/fields/",
            {
                "name": "comment",
                "label": "Comment",
                "field_type": "text",
                "required": False,
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


class NestedActionViewTest(WorkflowViewTestBase):
    """Tests for nested state action endpoints."""

    def test_list_actions(self):
        WorkflowStateAction.objects.create(
            state=self.state1,
            label="Test Action",
            backend_path="workflows.actions.tags.AddTagAction",
        )
        resp = self.client.get(
            f"/api/v1/workflow-templates/{self.workflow.pk}"
            f"/states/{self.state1.pk}/actions/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)


class NestedEscalationViewTest(WorkflowViewTestBase):
    """Tests for nested state escalation endpoints."""

    def test_list_escalations(self):
        WorkflowStateEscalation.objects.create(
            state=self.state1,
            transition=self.transition1,
            amount=2,
            unit="days",
        )
        resp = self.client.get(
            f"/api/v1/workflow-templates/{self.workflow.pk}"
            f"/states/{self.state1.pk}/escalations/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)


class DocumentWorkflowViewTest(WorkflowViewTestBase):
    """Tests for document workflow operations."""

    def test_list_document_workflows(self):
        resp = self.client.get(
            f"/api/v1/documents/{self.doc.pk}/workflows/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    def test_launch_workflow(self):
        resp = self.client.post(
            f"/api/v1/documents/{self.doc.pk}/workflows/launch/",
            {"workflow_template_id": self.workflow.pk},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["workflow_label"], "Test Workflow")
        self.assertEqual(resp.data["current_state_label"], "Draft")

    def test_launch_workflow_missing_template(self):
        resp = self.client.post(
            f"/api/v1/documents/{self.doc.pk}/workflows/launch/",
            {},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_execute_transition(self):
        instance = launch(self.doc, self.workflow, user=self.user)
        resp = self.client.post(
            f"/api/v1/documents/{self.doc.pk}/workflows/"
            f"{instance.pk}/transitions/{self.transition1.pk}/execute/",
            {"comment": "Ready for review"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["current_state_label"], "Review")

    def test_execute_transition_with_field_values(self):
        WorkflowTransitionField.objects.create(
            transition=self.transition1,
            name="priority",
            label="Priority",
            field_type="char",
        )
        instance = launch(self.doc, self.workflow, user=self.user)
        resp = self.client.post(
            f"/api/v1/documents/{self.doc.pk}/workflows/"
            f"{instance.pk}/transitions/{self.transition1.pk}/execute/",
            {
                "field_values": {"priority": "high"},
                "comment": "Urgent",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        instance.refresh_from_db()
        self.assertEqual(instance.context["priority"], "high")

    def test_get_log(self):
        instance = launch(self.doc, self.workflow, user=self.user)
        resp = self.client.get(
            f"/api/v1/documents/{self.doc.pk}/workflows/{instance.pk}/log/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)  # launch entry

    def test_available_transitions(self):
        instance = launch(self.doc, self.workflow, user=self.user)
        resp = self.client.get(
            f"/api/v1/documents/{self.doc.pk}/workflows/"
            f"{instance.pk}/available-transitions/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["label"], "Submit")

    def test_full_workflow_lifecycle_via_api(self):
        # Launch
        resp = self.client.post(
            f"/api/v1/documents/{self.doc.pk}/workflows/launch/",
            {"workflow_template_id": self.workflow.pk},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        instance_id = resp.data["id"]

        # Submit
        resp = self.client.post(
            f"/api/v1/documents/{self.doc.pk}/workflows/"
            f"{instance_id}/transitions/{self.transition1.pk}/execute/",
            {"comment": "Submitting"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["current_state_label"], "Review")
        self.assertFalse(resp.data["is_complete"])

        # Approve
        resp = self.client.post(
            f"/api/v1/documents/{self.doc.pk}/workflows/"
            f"{instance_id}/transitions/{self.transition2.pk}/execute/",
            {"comment": "Approved"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["current_state_label"], "Approved")
        self.assertTrue(resp.data["is_complete"])

        # Check log
        resp = self.client.get(
            f"/api/v1/documents/{self.doc.pk}/workflows/{instance_id}/log/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 3)

        # No more transitions available
        resp = self.client.get(
            f"/api/v1/documents/{self.doc.pk}/workflows/"
            f"{instance_id}/available-transitions/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)


class ActionBackendListViewTest(TestCase):
    """Tests for ActionBackendListView."""

    def setUp(self):
        self.user = User.objects.create_superuser(
            "admin", "admin@test.com", "adminpass"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_list_backends(self):
        resp = self.client.get("/api/v1/workflow-action-backends/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(len(resp.data) > 0)
        backend_paths = [b["backend_path"] for b in resp.data]
        self.assertIn(
            "workflows.actions.email.SendEmailAction", backend_paths
        )


class UnauthenticatedAccessTest(TestCase):
    """Tests that unauthenticated users cannot access workflow endpoints."""

    def test_templates_require_auth(self):
        client = APIClient()
        resp = client.get("/api/v1/workflow-templates/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

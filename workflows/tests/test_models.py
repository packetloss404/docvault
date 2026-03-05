"""Tests for workflow models."""

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from documents.models import Document, DocumentType
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


class WorkflowTemplateModelTest(TestCase):
    """Tests for WorkflowTemplate model."""

    def test_create_template(self):
        t = WorkflowTemplate.objects.create(label="Invoice Approval")
        self.assertEqual(t.label, "Invoice Approval")
        self.assertEqual(t.internal_name, "invoice-approval")
        self.assertFalse(t.auto_launch)

    def test_auto_slug(self):
        t = WorkflowTemplate.objects.create(label="Document Review Process")
        self.assertEqual(t.internal_name, "document-review-process")

    def test_explicit_slug(self):
        t = WorkflowTemplate.objects.create(
            label="Invoice Approval", internal_name="inv-appr"
        )
        self.assertEqual(t.internal_name, "inv-appr")

    def test_unique_internal_name(self):
        WorkflowTemplate.objects.create(label="Test", internal_name="test")
        with self.assertRaises(IntegrityError):
            WorkflowTemplate.objects.create(label="Test 2", internal_name="test")

    def test_str(self):
        t = WorkflowTemplate.objects.create(label="Invoice Approval")
        self.assertEqual(str(t), "Invoice Approval")

    def test_document_types_m2m(self):
        t = WorkflowTemplate.objects.create(label="Test Workflow")
        dt = DocumentType.objects.create(name="Invoice")
        t.document_types.add(dt)
        self.assertIn(dt, t.document_types.all())

    def test_ordering(self):
        WorkflowTemplate.objects.create(label="Zeta")
        WorkflowTemplate.objects.create(label="Alpha")
        labels = list(WorkflowTemplate.objects.values_list("label", flat=True))
        self.assertEqual(labels, ["Alpha", "Zeta"])

    def test_auditable_fields(self):
        t = WorkflowTemplate.objects.create(label="Test")
        self.assertIsNotNone(t.created_at)
        self.assertIsNotNone(t.updated_at)


class WorkflowStateModelTest(TestCase):
    """Tests for WorkflowState model."""

    def setUp(self):
        self.workflow = WorkflowTemplate.objects.create(label="Test Workflow")

    def test_create_state(self):
        s = WorkflowState.objects.create(
            workflow=self.workflow, label="Draft", initial=True, completion=0
        )
        self.assertEqual(s.label, "Draft")
        self.assertTrue(s.initial)

    def test_unique_label_per_workflow(self):
        WorkflowState.objects.create(workflow=self.workflow, label="Draft")
        with self.assertRaises(IntegrityError):
            WorkflowState.objects.create(workflow=self.workflow, label="Draft")

    def test_same_label_different_workflows(self):
        wf2 = WorkflowTemplate.objects.create(label="Other Workflow")
        WorkflowState.objects.create(workflow=self.workflow, label="Draft")
        WorkflowState.objects.create(workflow=wf2, label="Draft")
        self.assertEqual(WorkflowState.objects.filter(label="Draft").count(), 2)

    def test_cascade_delete(self):
        WorkflowState.objects.create(workflow=self.workflow, label="Draft")
        self.workflow.delete()
        self.assertEqual(WorkflowState.objects.count(), 0)

    def test_str(self):
        s = WorkflowState.objects.create(workflow=self.workflow, label="Draft")
        self.assertEqual(str(s), "Test Workflow - Draft")

    def test_completion_default(self):
        s = WorkflowState.objects.create(workflow=self.workflow, label="Start")
        self.assertEqual(s.completion, 0)

    def test_final_state(self):
        s = WorkflowState.objects.create(
            workflow=self.workflow, label="Approved", final=True, completion=100
        )
        self.assertTrue(s.final)
        self.assertEqual(s.completion, 100)


class WorkflowTransitionModelTest(TestCase):
    """Tests for WorkflowTransition model."""

    def setUp(self):
        self.workflow = WorkflowTemplate.objects.create(label="Test Workflow")
        self.state1 = WorkflowState.objects.create(
            workflow=self.workflow, label="Draft", initial=True
        )
        self.state2 = WorkflowState.objects.create(
            workflow=self.workflow, label="Review"
        )

    def test_create_transition(self):
        t = WorkflowTransition.objects.create(
            workflow=self.workflow,
            label="Submit",
            origin_state=self.state1,
            destination_state=self.state2,
        )
        self.assertEqual(t.label, "Submit")

    def test_str(self):
        t = WorkflowTransition.objects.create(
            workflow=self.workflow,
            label="Submit",
            origin_state=self.state1,
            destination_state=self.state2,
        )
        self.assertEqual(str(t), "Submit (Draft -> Review)")

    def test_cascade_delete_workflow(self):
        WorkflowTransition.objects.create(
            workflow=self.workflow,
            label="Submit",
            origin_state=self.state1,
            destination_state=self.state2,
        )
        self.workflow.delete()
        self.assertEqual(WorkflowTransition.objects.count(), 0)

    def test_validation_cross_workflow_origin(self):
        other_wf = WorkflowTemplate.objects.create(label="Other")
        other_state = WorkflowState.objects.create(
            workflow=other_wf, label="Foreign"
        )
        with self.assertRaises(ValidationError):
            WorkflowTransition.objects.create(
                workflow=self.workflow,
                label="Bad",
                origin_state=other_state,
                destination_state=self.state2,
            )

    def test_validation_cross_workflow_destination(self):
        other_wf = WorkflowTemplate.objects.create(label="Other")
        other_state = WorkflowState.objects.create(
            workflow=other_wf, label="Foreign"
        )
        with self.assertRaises(ValidationError):
            WorkflowTransition.objects.create(
                workflow=self.workflow,
                label="Bad",
                origin_state=self.state1,
                destination_state=other_state,
            )

    def test_condition_field(self):
        t = WorkflowTransition.objects.create(
            workflow=self.workflow,
            label="Submit",
            origin_state=self.state1,
            destination_state=self.state2,
            condition="context.get('approved') == True",
        )
        self.assertIn("approved", t.condition)


class WorkflowTransitionFieldModelTest(TestCase):
    """Tests for WorkflowTransitionField model."""

    def setUp(self):
        self.workflow = WorkflowTemplate.objects.create(label="Test")
        self.state1 = WorkflowState.objects.create(
            workflow=self.workflow, label="A", initial=True
        )
        self.state2 = WorkflowState.objects.create(
            workflow=self.workflow, label="B"
        )
        self.transition = WorkflowTransition.objects.create(
            workflow=self.workflow,
            label="Go",
            origin_state=self.state1,
            destination_state=self.state2,
        )

    def test_create_field(self):
        f = WorkflowTransitionField.objects.create(
            transition=self.transition,
            name="reason",
            label="Reason",
            field_type="text",
            required=True,
        )
        self.assertEqual(f.name, "reason")
        self.assertTrue(f.required)

    def test_cascade_delete(self):
        WorkflowTransitionField.objects.create(
            transition=self.transition,
            name="reason",
            label="Reason",
        )
        self.transition.delete()
        self.assertEqual(WorkflowTransitionField.objects.count(), 0)


class WorkflowStateActionModelTest(TestCase):
    """Tests for WorkflowStateAction model."""

    def setUp(self):
        self.workflow = WorkflowTemplate.objects.create(label="Test")
        self.state = WorkflowState.objects.create(
            workflow=self.workflow, label="Active"
        )

    def test_create_action(self):
        a = WorkflowStateAction.objects.create(
            state=self.state,
            label="Send Email",
            backend_path="workflows.actions.email.SendEmailAction",
            backend_data={"recipient": "admin@example.com"},
        )
        self.assertEqual(a.label, "Send Email")
        self.assertTrue(a.enabled)

    def test_str(self):
        a = WorkflowStateAction.objects.create(
            state=self.state,
            label="Send Email",
            when="on_entry",
            backend_path="workflows.actions.email.SendEmailAction",
        )
        self.assertEqual(str(a), "Active - Send Email (On entry)")

    def test_cascade_delete(self):
        WorkflowStateAction.objects.create(
            state=self.state,
            label="Test",
            backend_path="test.Action",
        )
        self.state.delete()
        self.assertEqual(WorkflowStateAction.objects.count(), 0)


class WorkflowStateEscalationModelTest(TestCase):
    """Tests for WorkflowStateEscalation model."""

    def setUp(self):
        self.workflow = WorkflowTemplate.objects.create(label="Test")
        self.state1 = WorkflowState.objects.create(
            workflow=self.workflow, label="Waiting", initial=True
        )
        self.state2 = WorkflowState.objects.create(
            workflow=self.workflow, label="Escalated"
        )
        self.transition = WorkflowTransition.objects.create(
            workflow=self.workflow,
            label="Escalate",
            origin_state=self.state1,
            destination_state=self.state2,
        )

    def test_create_escalation(self):
        e = WorkflowStateEscalation.objects.create(
            state=self.state1,
            transition=self.transition,
            amount=3,
            unit="days",
        )
        self.assertEqual(e.amount, 3)
        self.assertEqual(e.unit, "days")
        self.assertTrue(e.enabled)

    def test_str(self):
        e = WorkflowStateEscalation.objects.create(
            state=self.state1,
            transition=self.transition,
            amount=48,
            unit="hours",
        )
        self.assertEqual(str(e), "Waiting - escalate after 48 hours")

    def test_cascade_delete(self):
        WorkflowStateEscalation.objects.create(
            state=self.state1,
            transition=self.transition,
            amount=1,
            unit="days",
        )
        self.state1.delete()
        self.assertEqual(WorkflowStateEscalation.objects.count(), 0)


class WorkflowInstanceModelTest(TestCase):
    """Tests for WorkflowInstance model."""

    def setUp(self):
        self.workflow = WorkflowTemplate.objects.create(label="Test")
        self.state = WorkflowState.objects.create(
            workflow=self.workflow, label="Draft", initial=True
        )
        self.final_state = WorkflowState.objects.create(
            workflow=self.workflow, label="Done", final=True, completion=100
        )
        self.doc = Document.objects.create(title="Doc 1", filename="d1.pdf")

    def test_create_instance(self):
        inst = WorkflowInstance.objects.create(
            workflow=self.workflow,
            document=self.doc,
            current_state=self.state,
        )
        self.assertIsNotNone(inst.launched_at)
        self.assertFalse(inst.is_complete)

    def test_is_complete(self):
        inst = WorkflowInstance.objects.create(
            workflow=self.workflow,
            document=self.doc,
            current_state=self.final_state,
        )
        self.assertTrue(inst.is_complete)

    def test_unique_workflow_per_document(self):
        WorkflowInstance.objects.create(
            workflow=self.workflow,
            document=self.doc,
            current_state=self.state,
        )
        with self.assertRaises(IntegrityError):
            WorkflowInstance.objects.create(
                workflow=self.workflow,
                document=self.doc,
                current_state=self.state,
            )

    def test_different_documents_same_workflow(self):
        doc2 = Document.objects.create(title="Doc 2", filename="d2.pdf")
        WorkflowInstance.objects.create(
            workflow=self.workflow,
            document=self.doc,
            current_state=self.state,
        )
        WorkflowInstance.objects.create(
            workflow=self.workflow,
            document=doc2,
            current_state=self.state,
        )
        self.assertEqual(WorkflowInstance.objects.count(), 2)

    def test_cascade_delete_document(self):
        WorkflowInstance.objects.create(
            workflow=self.workflow,
            document=self.doc,
            current_state=self.state,
        )
        self.doc.hard_delete()
        self.assertEqual(WorkflowInstance.objects.count(), 0)

    def test_str(self):
        inst = WorkflowInstance.objects.create(
            workflow=self.workflow,
            document=self.doc,
            current_state=self.state,
        )
        self.assertIn("Test", str(inst))
        self.assertIn("Draft", str(inst))

    def test_context_default(self):
        inst = WorkflowInstance.objects.create(
            workflow=self.workflow,
            document=self.doc,
            current_state=self.state,
        )
        self.assertEqual(inst.context, {})


class WorkflowInstanceLogEntryModelTest(TestCase):
    """Tests for WorkflowInstanceLogEntry model."""

    def setUp(self):
        self.workflow = WorkflowTemplate.objects.create(label="Test")
        self.state = WorkflowState.objects.create(
            workflow=self.workflow, label="Draft", initial=True
        )
        self.doc = Document.objects.create(title="Doc 1", filename="d1.pdf")
        self.instance = WorkflowInstance.objects.create(
            workflow=self.workflow,
            document=self.doc,
            current_state=self.state,
        )
        self.user = User.objects.create_user("testuser", password="testpass")

    def test_create_log_entry(self):
        entry = WorkflowInstanceLogEntry.objects.create(
            instance=self.instance,
            user=self.user,
            comment="Workflow launched.",
        )
        self.assertIsNotNone(entry.datetime)
        self.assertEqual(entry.comment, "Workflow launched.")

    def test_cascade_delete(self):
        WorkflowInstanceLogEntry.objects.create(
            instance=self.instance,
            comment="Test",
        )
        self.instance.delete()
        self.assertEqual(WorkflowInstanceLogEntry.objects.count(), 0)

    def test_ordering(self):
        e1 = WorkflowInstanceLogEntry.objects.create(
            instance=self.instance, comment="First"
        )
        e2 = WorkflowInstanceLogEntry.objects.create(
            instance=self.instance, comment="Second"
        )
        entries = list(
            WorkflowInstanceLogEntry.objects.filter(
                instance=self.instance
            ).values_list("comment", flat=True)
        )
        # Ordered by -datetime, so most recent first
        self.assertEqual(entries[0], "Second")

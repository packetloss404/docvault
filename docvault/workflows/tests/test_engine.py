"""Tests for the workflow engine."""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from documents.models import Document
from workflows.engine import (
    check_escalations,
    do_transition,
    get_available_transitions,
    launch,
)
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


class LaunchTest(TestCase):
    """Tests for workflow launch."""

    def setUp(self):
        self.user = User.objects.create_user("testuser", password="testpass")
        self.doc = Document.objects.create(title="Test Doc", filename="test.pdf")
        self.workflow = WorkflowTemplate.objects.create(label="Approval")
        self.initial_state = WorkflowState.objects.create(
            workflow=self.workflow, label="Draft", initial=True, completion=0
        )
        self.final_state = WorkflowState.objects.create(
            workflow=self.workflow, label="Approved", final=True, completion=100
        )

    def test_launch_creates_instance(self):
        instance = launch(self.doc, self.workflow, user=self.user)
        self.assertIsNotNone(instance.pk)
        self.assertEqual(instance.workflow, self.workflow)
        self.assertEqual(instance.document, self.doc)
        self.assertEqual(instance.current_state, self.initial_state)
        self.assertEqual(instance.context, {})

    def test_launch_creates_log_entry(self):
        instance = launch(self.doc, self.workflow, user=self.user)
        entries = WorkflowInstanceLogEntry.objects.filter(instance=instance)
        self.assertEqual(entries.count(), 1)
        self.assertEqual(entries.first().user, self.user)
        self.assertIn("launched", entries.first().comment.lower())

    def test_launch_no_initial_state_raises(self):
        wf = WorkflowTemplate.objects.create(label="No Initial")
        WorkflowState.objects.create(workflow=wf, label="Not initial")
        with self.assertRaises(ValueError) as ctx:
            launch(self.doc, wf)
        self.assertIn("no initial state", str(ctx.exception).lower())

    def test_launch_runs_entry_actions(self):
        WorkflowStateAction.objects.create(
            state=self.initial_state,
            label="Test Action",
            when="on_entry",
            backend_path="workflows.actions.document_properties.SetDocumentPropertiesAction",
            backend_data={"title": "Modified by workflow"},
        )
        launch(self.doc, self.workflow)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.title, "Modified by workflow")


class DoTransitionTest(TestCase):
    """Tests for transition execution."""

    def setUp(self):
        self.user = User.objects.create_user("testuser", password="testpass")
        self.doc = Document.objects.create(title="Test Doc", filename="test.pdf")
        self.workflow = WorkflowTemplate.objects.create(label="Approval")
        self.draft = WorkflowState.objects.create(
            workflow=self.workflow, label="Draft", initial=True, completion=0
        )
        self.review = WorkflowState.objects.create(
            workflow=self.workflow, label="Review", completion=50
        )
        self.approved = WorkflowState.objects.create(
            workflow=self.workflow, label="Approved", final=True, completion=100
        )
        self.submit = WorkflowTransition.objects.create(
            workflow=self.workflow,
            label="Submit",
            origin_state=self.draft,
            destination_state=self.review,
        )
        self.approve = WorkflowTransition.objects.create(
            workflow=self.workflow,
            label="Approve",
            origin_state=self.review,
            destination_state=self.approved,
        )
        self.instance = launch(self.doc, self.workflow)

    def test_transition_moves_state(self):
        do_transition(self.instance, self.submit, user=self.user)
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.current_state, self.review)

    def test_transition_creates_log_entry(self):
        do_transition(self.instance, self.submit, user=self.user, comment="Ready")
        entries = WorkflowInstanceLogEntry.objects.filter(
            instance=self.instance, transition=self.submit
        )
        self.assertEqual(entries.count(), 1)
        self.assertEqual(entries.first().comment, "Ready")

    def test_transition_wrong_state_raises(self):
        with self.assertRaises(ValueError) as ctx:
            do_transition(self.instance, self.approve, user=self.user)
        self.assertIn("requires state", str(ctx.exception))

    def test_transition_updates_context(self):
        do_transition(
            self.instance, self.submit, user=self.user,
            field_values={"reason": "Complete"},
        )
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.context["reason"], "Complete")

    def test_transition_validates_required_fields(self):
        WorkflowTransitionField.objects.create(
            transition=self.submit,
            name="reason",
            label="Reason",
            required=True,
        )
        with self.assertRaises(ValueError) as ctx:
            do_transition(self.instance, self.submit, user=self.user)
        self.assertIn("Reason", str(ctx.exception))

    def test_transition_with_required_field_provided(self):
        WorkflowTransitionField.objects.create(
            transition=self.submit,
            name="reason",
            label="Reason",
            required=True,
        )
        do_transition(
            self.instance, self.submit, user=self.user,
            field_values={"reason": "Ready for review"},
        )
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.current_state, self.review)

    def test_transition_with_condition_pass(self):
        self.submit.condition = "True"
        self.submit.save(update_fields=["condition"])
        do_transition(self.instance, self.submit)
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.current_state, self.review)

    def test_transition_with_condition_fail(self):
        self.submit.condition = "False"
        self.submit.save(update_fields=["condition"])
        with self.assertRaises(ValueError) as ctx:
            do_transition(self.instance, self.submit)
        self.assertIn("condition not met", str(ctx.exception).lower())

    def test_cannot_transition_complete_instance(self):
        do_transition(self.instance, self.submit)
        do_transition(self.instance, self.approve)
        self.instance.refresh_from_db()
        self.assertTrue(self.instance.is_complete)

        reject = WorkflowTransition.objects.create(
            workflow=self.workflow,
            label="Reopen",
            origin_state=self.approved,
            destination_state=self.draft,
        )
        with self.assertRaises(ValueError) as ctx:
            do_transition(self.instance, reject)
        self.assertIn("completed", str(ctx.exception).lower())

    def test_full_lifecycle(self):
        # Draft -> Review -> Approved
        do_transition(self.instance, self.submit, user=self.user)
        self.instance.refresh_from_db()
        self.assertFalse(self.instance.is_complete)

        do_transition(self.instance, self.approve, user=self.user)
        self.instance.refresh_from_db()
        self.assertTrue(self.instance.is_complete)
        self.assertEqual(self.instance.current_state, self.approved)

        log_count = WorkflowInstanceLogEntry.objects.filter(
            instance=self.instance
        ).count()
        self.assertEqual(log_count, 3)  # launch + submit + approve


class GetAvailableTransitionsTest(TestCase):
    """Tests for available transition retrieval."""

    def setUp(self):
        self.doc = Document.objects.create(title="Test Doc", filename="test.pdf")
        self.workflow = WorkflowTemplate.objects.create(label="WF")
        self.s1 = WorkflowState.objects.create(
            workflow=self.workflow, label="S1", initial=True
        )
        self.s2 = WorkflowState.objects.create(
            workflow=self.workflow, label="S2"
        )
        self.s3 = WorkflowState.objects.create(
            workflow=self.workflow, label="S3", final=True
        )
        self.t1 = WorkflowTransition.objects.create(
            workflow=self.workflow, label="T1",
            origin_state=self.s1, destination_state=self.s2,
        )
        self.t2 = WorkflowTransition.objects.create(
            workflow=self.workflow, label="T2",
            origin_state=self.s1, destination_state=self.s3,
        )
        self.t3 = WorkflowTransition.objects.create(
            workflow=self.workflow, label="T3",
            origin_state=self.s2, destination_state=self.s3,
        )
        self.instance = launch(self.doc, self.workflow)

    def test_returns_transitions_from_current_state(self):
        available = get_available_transitions(self.instance)
        self.assertEqual(available.count(), 2)
        labels = set(available.values_list("label", flat=True))
        self.assertEqual(labels, {"T1", "T2"})

    def test_filters_by_condition(self):
        self.t2.condition = "False"
        self.t2.save(update_fields=["condition"])
        available = get_available_transitions(self.instance)
        self.assertEqual(available.count(), 1)
        self.assertEqual(available.first().label, "T1")

    def test_no_transitions_for_final_state(self):
        do_transition(self.instance, self.t2)
        self.instance.refresh_from_db()
        available = get_available_transitions(self.instance)
        self.assertEqual(available.count(), 0)


class CheckEscalationsTest(TestCase):
    """Tests for escalation checking."""

    def setUp(self):
        self.doc = Document.objects.create(title="Test Doc", filename="test.pdf")
        self.workflow = WorkflowTemplate.objects.create(label="WF")
        self.s1 = WorkflowState.objects.create(
            workflow=self.workflow, label="Waiting", initial=True
        )
        self.s2 = WorkflowState.objects.create(
            workflow=self.workflow, label="Escalated"
        )
        self.t1 = WorkflowTransition.objects.create(
            workflow=self.workflow, label="Auto Escalate",
            origin_state=self.s1, destination_state=self.s2,
        )
        self.instance = launch(self.doc, self.workflow)

    def test_escalation_triggers_when_overdue(self):
        WorkflowStateEscalation.objects.create(
            state=self.s1,
            transition=self.t1,
            amount=1,
            unit="hours",
        )
        # Set state_changed_at to 2 hours ago
        self.instance.state_changed_at = timezone.now() - timedelta(hours=2)
        self.instance.save(update_fields=["state_changed_at"])

        count = check_escalations()
        self.assertEqual(count, 1)
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.current_state, self.s2)

    def test_escalation_does_not_trigger_when_not_overdue(self):
        WorkflowStateEscalation.objects.create(
            state=self.s1,
            transition=self.t1,
            amount=24,
            unit="hours",
        )
        count = check_escalations()
        self.assertEqual(count, 0)
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.current_state, self.s1)

    def test_disabled_escalation_ignored(self):
        WorkflowStateEscalation.objects.create(
            state=self.s1,
            transition=self.t1,
            amount=1,
            unit="minutes",
            enabled=False,
        )
        self.instance.state_changed_at = timezone.now() - timedelta(hours=1)
        self.instance.save(update_fields=["state_changed_at"])

        count = check_escalations()
        self.assertEqual(count, 0)

    def test_escalation_with_condition(self):
        WorkflowStateEscalation.objects.create(
            state=self.s1,
            transition=self.t1,
            amount=1,
            unit="minutes",
            condition="context.get('urgent', False)",
        )
        self.instance.state_changed_at = timezone.now() - timedelta(hours=1)
        self.instance.context = {"urgent": False}
        self.instance.save(update_fields=["state_changed_at", "context"])

        count = check_escalations()
        self.assertEqual(count, 0)

        # Now set urgent to True
        self.instance.context = {"urgent": True}
        self.instance.save(update_fields=["context"])

        count = check_escalations()
        self.assertEqual(count, 1)

"""Tests for workflow serializers."""

from django.contrib.auth.models import User
from django.test import TestCase

from documents.models import Document
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
from workflows.serializers import (
    TransitionExecuteSerializer,
    WorkflowInstanceSerializer,
    WorkflowStateSerializer,
    WorkflowTemplateSerializer,
    WorkflowTransitionSerializer,
)


class WorkflowTemplateSerializerTest(TestCase):
    """Tests for WorkflowTemplateSerializer."""

    def test_serialization(self):
        t = WorkflowTemplate.objects.create(label="Test WF")
        WorkflowState.objects.create(workflow=t, label="S1")
        WorkflowState.objects.create(workflow=t, label="S2")
        s = WorkflowTemplateSerializer(t)
        data = s.data
        self.assertEqual(data["label"], "Test WF")
        self.assertEqual(data["state_count"], 2)
        self.assertEqual(data["transition_count"], 0)
        self.assertIn("created_at", data)

    def test_read_only_fields(self):
        s = WorkflowTemplateSerializer()
        read_only = s.Meta.read_only_fields
        self.assertIn("id", read_only)
        self.assertIn("internal_name", read_only)


class WorkflowStateSerializerTest(TestCase):
    """Tests for WorkflowStateSerializer."""

    def test_serialization(self):
        wf = WorkflowTemplate.objects.create(label="WF")
        state = WorkflowState.objects.create(
            workflow=wf, label="Draft", initial=True, completion=25
        )
        s = WorkflowStateSerializer(state)
        data = s.data
        self.assertEqual(data["label"], "Draft")
        self.assertTrue(data["initial"])
        self.assertEqual(data["completion"], 25)


class WorkflowTransitionSerializerTest(TestCase):
    """Tests for WorkflowTransitionSerializer."""

    def test_includes_state_labels(self):
        wf = WorkflowTemplate.objects.create(label="WF")
        s1 = WorkflowState.objects.create(workflow=wf, label="Draft")
        s2 = WorkflowState.objects.create(workflow=wf, label="Review")
        t = WorkflowTransition.objects.create(
            workflow=wf, label="Submit",
            origin_state=s1, destination_state=s2,
        )
        s = WorkflowTransitionSerializer(t)
        data = s.data
        self.assertEqual(data["origin_state_label"], "Draft")
        self.assertEqual(data["destination_state_label"], "Review")


class WorkflowInstanceSerializerTest(TestCase):
    """Tests for WorkflowInstanceSerializer."""

    def test_serialization(self):
        wf = WorkflowTemplate.objects.create(label="WF")
        state = WorkflowState.objects.create(
            workflow=wf, label="Draft", initial=True, completion=10
        )
        doc = Document.objects.create(title="Doc", filename="d.pdf")
        inst = WorkflowInstance.objects.create(
            workflow=wf, document=doc, current_state=state
        )
        s = WorkflowInstanceSerializer(inst)
        data = s.data
        self.assertEqual(data["workflow_label"], "WF")
        self.assertEqual(data["current_state_label"], "Draft")
        self.assertFalse(data["is_complete"])
        self.assertEqual(data["completion"], 10)

    def test_complete_instance(self):
        wf = WorkflowTemplate.objects.create(label="WF")
        final = WorkflowState.objects.create(
            workflow=wf, label="Done", final=True, completion=100
        )
        doc = Document.objects.create(title="Doc", filename="dc.pdf")
        inst = WorkflowInstance.objects.create(
            workflow=wf, document=doc, current_state=final
        )
        s = WorkflowInstanceSerializer(inst)
        self.assertTrue(s.data["is_complete"])


class TransitionExecuteSerializerTest(TestCase):
    """Tests for TransitionExecuteSerializer."""

    def test_valid_data(self):
        s = TransitionExecuteSerializer(data={
            "field_values": {"reason": "Complete"},
            "comment": "Looks good",
        })
        self.assertTrue(s.is_valid())
        self.assertEqual(s.validated_data["field_values"]["reason"], "Complete")
        self.assertEqual(s.validated_data["comment"], "Looks good")

    def test_empty_data_valid(self):
        s = TransitionExecuteSerializer(data={})
        self.assertTrue(s.is_valid())
        self.assertEqual(s.validated_data["field_values"], {})
        self.assertEqual(s.validated_data["comment"], "")

    def test_defaults(self):
        s = TransitionExecuteSerializer(data={})
        s.is_valid()
        self.assertEqual(s.validated_data["field_values"], {})

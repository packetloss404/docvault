"""Tests for workflow action backends."""

from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase

from documents.models import Document, DocumentType
from organization.models import MetadataType, Tag
from workflows.actions.cabinet import AddToCabinetAction
from workflows.actions.document_properties import SetDocumentPropertiesAction
from workflows.actions.email import SendEmailAction
from workflows.actions.launch_workflow import LaunchWorkflowAction
from workflows.actions.metadata import SetMetadataAction
from workflows.actions.tags import AddTagAction
from workflows.actions.webhook import WebhookAction
from workflows.engine import launch
from workflows.models import (
    WorkflowInstance,
    WorkflowState,
    WorkflowTemplate,
)


class ActionTestBase(TestCase):
    """Base for action tests with common setup."""

    def setUp(self):
        self.user = User.objects.create_user("actionuser", password="pass")
        self.doc = Document.objects.create(
            title="Original Title", filename="action_test.pdf", owner=self.user
        )
        self.workflow = WorkflowTemplate.objects.create(label="Action Test WF")
        self.state = WorkflowState.objects.create(
            workflow=self.workflow, label="Active", initial=True
        )
        self.instance = WorkflowInstance.objects.create(
            workflow=self.workflow,
            document=self.doc,
            current_state=self.state,
            context={"test_key": "test_value"},
        )


class SetDocumentPropertiesActionTest(ActionTestBase):
    """Tests for SetDocumentPropertiesAction."""

    def test_set_title(self):
        action = SetDocumentPropertiesAction()
        action.execute(self.instance, {"title": "New Title"})
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.title, "New Title")

    def test_set_language(self):
        action = SetDocumentPropertiesAction()
        action.execute(self.instance, {"language": "de"})
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.language, "de")

    def test_set_document_type(self):
        dt = DocumentType.objects.create(name="Invoice")
        action = SetDocumentPropertiesAction()
        action.execute(self.instance, {"document_type_id": dt.pk})
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.document_type, dt)

    def test_set_multiple_properties(self):
        action = SetDocumentPropertiesAction()
        action.execute(self.instance, {"title": "Changed", "language": "fr"})
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.title, "Changed")
        self.assertEqual(self.doc.language, "fr")

    def test_validate_config_empty(self):
        action = SetDocumentPropertiesAction()
        errors = action.validate_config({})
        self.assertTrue(len(errors) > 0)


class AddTagActionTest(ActionTestBase):
    """Tests for AddTagAction."""

    def test_add_tags(self):
        tag1 = Tag.objects.create(name="Urgent", owner=self.user)
        tag2 = Tag.objects.create(name="Review", owner=self.user)
        action = AddTagAction()
        action.execute(self.instance, {"tag_ids": [tag1.pk, tag2.pk]})
        self.assertEqual(self.doc.tags.count(), 2)
        self.assertIn(tag1, self.doc.tags.all())

    def test_add_empty_tag_ids(self):
        action = AddTagAction()
        action.execute(self.instance, {"tag_ids": []})
        self.assertEqual(self.doc.tags.count(), 0)

    def test_validate_missing_tag_ids(self):
        action = AddTagAction()
        errors = action.validate_config({})
        self.assertTrue(len(errors) > 0)


class AddToCabinetActionTest(ActionTestBase):
    """Tests for AddToCabinetAction."""

    def test_set_cabinet(self):
        from organization.models import Cabinet

        cabinet = Cabinet.objects.create(name="Archive", owner=self.user)
        action = AddToCabinetAction()
        action.execute(self.instance, {"cabinet_id": cabinet.pk})
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.cabinet, cabinet)


class SetMetadataActionTest(ActionTestBase):
    """Tests for SetMetadataAction."""

    def test_set_metadata(self):
        mt = MetadataType.objects.create(name="invoice_number", owner=self.user)
        action = SetMetadataAction()
        action.execute(self.instance, {
            "metadata_type_id": mt.pk,
            "value": "INV-001",
        })
        from organization.models import DocumentMetadata

        dm = DocumentMetadata.objects.get(document=self.doc, metadata_type=mt)
        self.assertEqual(dm.value, "INV-001")

    def test_update_existing_metadata(self):
        mt = MetadataType.objects.create(name="status", owner=self.user)
        from organization.models import DocumentMetadata

        DocumentMetadata.objects.create(
            document=self.doc, metadata_type=mt, value="old"
        )
        action = SetMetadataAction()
        action.execute(self.instance, {
            "metadata_type_id": mt.pk,
            "value": "new",
        })
        dm = DocumentMetadata.objects.get(document=self.doc, metadata_type=mt)
        self.assertEqual(dm.value, "new")


class LaunchWorkflowActionTest(ActionTestBase):
    """Tests for LaunchWorkflowAction."""

    def test_launch_another_workflow(self):
        other_wf = WorkflowTemplate.objects.create(label="Other Workflow")
        WorkflowState.objects.create(
            workflow=other_wf, label="Start", initial=True
        )
        action = LaunchWorkflowAction()
        action.execute(self.instance, {"workflow_template_id": other_wf.pk})
        self.assertEqual(
            WorkflowInstance.objects.filter(
                document=self.doc, workflow=other_wf
            ).count(),
            1,
        )

    def test_launch_nonexistent_template(self):
        action = LaunchWorkflowAction()
        # Should not raise, just log warning
        action.execute(self.instance, {"workflow_template_id": 99999})


class SendEmailActionTest(ActionTestBase):
    """Tests for SendEmailAction."""

    @patch("workflows.actions.email.send_mail")
    def test_send_email(self, mock_send):
        action = SendEmailAction()
        action.execute(self.instance, {
            "recipient": "admin@example.com",
            "subject": "Workflow update for {{ document.title }}",
            "body": "Document {{ document.title }} is now in {{ state.label }}.",
        })
        mock_send.assert_called_once()
        args = mock_send.call_args
        self.assertIn("Original Title", args[1]["subject"])
        self.assertEqual(args[1]["recipient_list"], ["admin@example.com"])

    @patch("workflows.actions.email.send_mail")
    def test_send_email_no_recipient(self, mock_send):
        action = SendEmailAction()
        action.execute(self.instance, {
            "recipient": "",
            "subject": "Test",
            "body": "Test",
        })
        mock_send.assert_not_called()


class WebhookActionTest(ActionTestBase):
    """Tests for WebhookAction."""

    @patch("workflows.actions.webhook.urllib.request.urlopen")
    def test_send_webhook(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        action = WebhookAction()
        action.execute(self.instance, {
            "url": "https://example.com/webhook",
            "method": "POST",
            "payload": '{"doc": "{{ document_title }}"}',
        })
        mock_urlopen.assert_called_once()

    def test_webhook_no_url(self):
        action = WebhookAction()
        # Should not raise, just log warning
        action.execute(self.instance, {"url": ""})

    def test_validate_config(self):
        action = WebhookAction()
        errors = action.validate_config({"url": "", "method": "DELETE"})
        self.assertTrue(len(errors) >= 2)  # Missing URL + invalid method

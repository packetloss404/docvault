"""Tests for the ZoneOCRPlugin."""

import pytest
from django.contrib.auth.models import User

from documents.models import Document
from processing.context import ProcessingContext
from zone_ocr.constants import FIELD_STRING, PREPROCESS_NONE
from zone_ocr.models import ZoneOCRField, ZoneOCRResult, ZoneOCRTemplate
from zone_ocr.plugin import ZoneOCRPlugin


@pytest.fixture
def user(db):
    return User.objects.create_user(username="pluginuser", password="testpass")


@pytest.fixture
def document(user):
    return Document.objects.create(
        title="Plugin Test Doc",
        content="Invoice Number: INV-999\nTotal: 500",
        owner=user,
    )


@pytest.fixture
def template(user):
    return ZoneOCRTemplate.objects.create(
        name="Plugin Template",
        is_active=True,
        created_by=user,
        updated_by=user,
    )


@pytest.fixture
def zone_field(template):
    return ZoneOCRField.objects.create(
        template=template,
        name="Invoice Number",
        field_type=FIELD_STRING,
        bounding_box={"x": 0, "y": 0, "width": 50, "height": 10},
        preprocessing=PREPROCESS_NONE,
    )


@pytest.mark.django_db
class TestZoneOCRPluginCanRun:
    def test_returns_false_when_no_document_id(self):
        plugin = ZoneOCRPlugin()
        context = ProcessingContext(content="some content", document_id=None)
        assert plugin.can_run(context) is False

    def test_returns_false_when_no_content(self, document):
        plugin = ZoneOCRPlugin()
        context = ProcessingContext(content="", document_id=document.pk)
        assert plugin.can_run(context) is False

    def test_returns_false_when_no_active_templates(self, document):
        plugin = ZoneOCRPlugin()
        context = ProcessingContext(content="some content", document_id=document.pk)
        # No templates exist
        assert plugin.can_run(context) is False

    def test_returns_true_when_templates_exist_and_content(self, document, template):
        plugin = ZoneOCRPlugin()
        context = ProcessingContext(content="some content", document_id=document.pk)
        assert plugin.can_run(context) is True

    def test_returns_false_when_template_inactive(self, document, template):
        template.is_active = False
        template.save()
        plugin = ZoneOCRPlugin()
        context = ProcessingContext(content="some content", document_id=document.pk)
        assert plugin.can_run(context) is False


@pytest.mark.django_db
class TestZoneOCRPluginProcess:
    def test_process_creates_results(self, document, template, zone_field):
        plugin = ZoneOCRPlugin()
        context = ProcessingContext(
            content="Invoice Number: INV-999\nTotal: 500",
            document_id=document.pk,
        )
        result = plugin.process(context)
        assert result.success is True
        assert ZoneOCRResult.objects.filter(document=document).count() == 1
        ocr_result = ZoneOCRResult.objects.get(document=document)
        assert ocr_result.extracted_value == "INV-999"

    def test_process_document_not_found(self, template, zone_field):
        plugin = ZoneOCRPlugin()
        context = ProcessingContext(content="anything", document_id=99999)
        result = plugin.process(context)
        assert result.success is False
        assert "not found" in result.message

    def test_process_no_matching_template_still_succeeds(self, user):
        # Create a template targeting page 5 and a document with 1 page
        doc = Document.objects.create(
            title="Short Doc",
            content="no matching fields here",
            page_count=1,
            owner=user,
        )
        tmpl = ZoneOCRTemplate.objects.create(
            name="Page 5 Template",
            page_number=5,
            is_active=True,
            created_by=user,
            updated_by=user,
        )
        ZoneOCRField.objects.create(
            template=tmpl,
            name="Unusual Field",
            field_type=FIELD_STRING,
            bounding_box={"x": 0, "y": 0, "width": 10, "height": 10},
        )
        plugin = ZoneOCRPlugin()
        context = ProcessingContext(content="no matching fields here", document_id=doc.pk)
        result = plugin.process(context)
        # The plugin falls back to the first eligible template
        assert result.success is True

    def test_plugin_metadata(self):
        plugin = ZoneOCRPlugin()
        assert plugin.name == "ZoneOCRPlugin"
        assert plugin.order == 107

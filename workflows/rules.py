"""Rule execution engine for trigger-action workflows."""

import fnmatch
import logging
import re

from django.core.mail import send_mail

from workflows.constants import (
    ACTION_ADD_TAG,
    ACTION_LAUNCH_WORKFLOW,
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
    TRIGGER_SCHEDULED,
)

logger = logging.getLogger(__name__)


def get_matching_rules(trigger_type, document=None, context=None):
    """Get all enabled rules whose triggers match for the given type and document."""
    from workflows.models import WorkflowRule

    rules = (
        WorkflowRule.objects.filter(
            enabled=True,
            triggers__type=trigger_type,
            triggers__enabled=True,
        )
        .distinct()
        .order_by("order", "name")
    )

    matched = []
    for rule in rules:
        triggers = rule.triggers.filter(type=trigger_type, enabled=True)
        for trigger in triggers:
            if _trigger_matches(trigger, document, context):
                matched.append(rule)
                break
    return matched


def _trigger_matches(trigger, document, context):
    """Check if a trigger's filters match the document/context."""
    if not document and trigger.type != TRIGGER_SCHEDULED:
        return False

    # Filename filter
    if trigger.filter_filename and document:
        filename = getattr(document, "filename", "") or ""
        if not fnmatch.fnmatch(filename.lower(), trigger.filter_filename.lower()):
            return False

    # Path filter
    if trigger.filter_path and context:
        source_path = str(getattr(context, "source_path", "") or "")
        if not fnmatch.fnmatch(source_path.lower(), trigger.filter_path.lower()):
            return False

    # Tag filter
    if trigger.filter_has_tags.exists() and document:
        required_tags = set(trigger.filter_has_tags.values_list("pk", flat=True))
        doc_tags = set(document.tags.values_list("pk", flat=True))
        if not required_tags.issubset(doc_tags):
            return False

    # Correspondent filter
    if trigger.filter_has_correspondent_id and document:
        if document.correspondent_id != trigger.filter_has_correspondent_id:
            return False

    # Document type filter
    if trigger.filter_has_document_type_id and document:
        if document.document_type_id != trigger.filter_has_document_type_id:
            return False

    # Text pattern matching
    if trigger.match_pattern and document:
        if not _matches_pattern(trigger, document):
            return False

    return True


def _matches_pattern(trigger, document):
    """Check if document content/title matches the trigger's pattern."""
    pattern = trigger.match_pattern
    algo = trigger.matching_algorithm
    text = f"{document.title} {document.content or ''}"

    if algo == MATCH_NONE:
        return True
    elif algo == MATCH_ANY:
        words = pattern.lower().split()
        text_lower = text.lower()
        return any(w in text_lower for w in words)
    elif algo == MATCH_ALL:
        words = pattern.lower().split()
        text_lower = text.lower()
        return all(w in text_lower for w in words)
    elif algo == MATCH_LITERAL:
        return pattern.lower() in text.lower()
    elif algo == MATCH_REGEX:
        try:
            return bool(re.search(pattern, text, re.IGNORECASE))
        except re.error:
            return False
    elif algo == MATCH_FUZZY:
        words = pattern.lower().split()
        text_lower = text.lower()
        if not words:
            return True
        matches = sum(1 for w in words if w in text_lower)
        return matches >= len(words) * 0.7
    return True


def execute_rule_actions(rule, document, user=None):
    """Execute all enabled actions for a rule against a document."""
    actions = rule.actions.filter(enabled=True).order_by("order", "id")
    for action in actions:
        try:
            _execute_action(action, document, user)
        except Exception:
            logger.exception(
                "Error executing action '%s' for rule '%s' on document %s",
                action,
                rule.name,
                document.pk,
            )


def _execute_action(action, document, user=None):
    """Execute a single action against a document."""
    config = action.configuration or {}

    if action.type == ACTION_ADD_TAG:
        tag_ids = config.get("tag_ids", [])
        if tag_ids:
            document.tags.add(*tag_ids)

    elif action.type == ACTION_REMOVE_TAG:
        tag_ids = config.get("tag_ids", [])
        if tag_ids:
            document.tags.remove(*tag_ids)

    elif action.type == ACTION_SET_CORRESPONDENT:
        correspondent_id = config.get("correspondent_id")
        if correspondent_id:
            document.correspondent_id = correspondent_id
            document.save(update_fields=["correspondent_id"])

    elif action.type == ACTION_SET_TYPE:
        doc_type_id = config.get("document_type_id")
        if doc_type_id:
            document.document_type_id = doc_type_id
            document.save(update_fields=["document_type_id"])

    elif action.type == ACTION_SET_STORAGE_PATH:
        path_id = config.get("storage_path_id")
        if path_id:
            document.storage_path_id = path_id
            document.save(update_fields=["storage_path_id"])

    elif action.type == ACTION_SET_CUSTOM_FIELD:
        from organization.models import CustomFieldInstance

        field_id = config.get("field_id")
        value = config.get("value")
        if field_id is not None:
            CustomFieldInstance.objects.update_or_create(
                document=document,
                field_id=field_id,
                defaults={"value_json": value},
            )

    elif action.type == ACTION_SEND_EMAIL:
        _send_email_action(config, document)

    elif action.type == ACTION_WEBHOOK:
        _send_webhook_action(config, document)

    elif action.type == ACTION_LAUNCH_WORKFLOW:
        template_id = config.get("workflow_template_id")
        if template_id:
            from workflows.engine import launch
            from workflows.models import WorkflowTemplate

            try:
                template = WorkflowTemplate.objects.get(pk=template_id)
                launch(document, template, user=user)
            except Exception:
                logger.exception(
                    "Failed to launch workflow %s for document %s",
                    template_id,
                    document.pk,
                )


def _render_placeholder(template_str, document):
    """Render a template string with document context using Jinja2 placeholders."""
    if not template_str:
        return template_str
    try:
        from jinja2 import Template

        tmpl = Template(template_str)
        return tmpl.render(
            document=document,
            tags=(
                list(document.tags.values_list("name", flat=True))
                if hasattr(document, "tags")
                else []
            ),
        )
    except Exception:
        logger.exception("Error rendering template: %s", template_str)
        return template_str


def _send_email_action(config, document):
    """Send email with rendered placeholders."""
    subject = _render_placeholder(config.get("subject", ""), document)
    body = _render_placeholder(config.get("body", ""), document)
    to = config.get("to", [])
    if isinstance(to, str):
        to = [to]
    if to:
        send_mail(subject, body, None, to, fail_silently=True)


def _send_webhook_action(config, document):
    """Send webhook with rendered payload."""
    import urllib.request

    url = config.get("url", "")
    method = config.get("method", "POST").upper()
    headers = config.get("headers", {})
    body_template = config.get("body", "")

    if not url:
        return

    body = _render_placeholder(body_template, document)

    headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(
        url,
        data=body.encode("utf-8") if body else None,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            logger.info("Webhook %s returned %s", url, response.status)
    except Exception:
        logger.exception("Webhook failed: %s", url)


def apply_consumption_overrides(rules, context):
    """Apply consumption trigger overrides to a ProcessingContext.

    For CONSUMPTION triggers, rule actions set overrides on the context
    before the document is created.
    """
    for rule in rules:
        actions = rule.actions.filter(enabled=True).order_by("order", "id")
        for action in actions:
            config = action.configuration or {}
            if action.type == ACTION_ADD_TAG:
                tag_ids = config.get("tag_ids", [])
                if tag_ids:
                    existing = context.override_tags or []
                    context.override_tags = list(set(existing + tag_ids))
            elif action.type == ACTION_SET_CORRESPONDENT:
                cid = config.get("correspondent_id")
                if cid:
                    context.override_correspondent = cid
            elif action.type == ACTION_SET_TYPE:
                tid = config.get("document_type_id")
                if tid:
                    context.override_document_type = tid

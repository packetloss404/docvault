"""Action to send a webhook HTTP request."""

import json
import logging
import urllib.request
import urllib.error

import jinja2

from .base import WorkflowAction

logger = logging.getLogger(__name__)


class WebhookAction(WorkflowAction):
    """
    Send an HTTP webhook request.

    Config keys:
    - url (str): Target URL.
    - method (str): HTTP method (POST or PUT). Default: POST.
    - payload (str): Jinja2 template for JSON payload.
    - headers (dict, optional): Extra HTTP headers.
    - timeout (int, optional): Timeout in seconds. Default: 10.
    """

    def execute(self, instance, config):
        url = config.get("url", "")
        method = config.get("method", "POST").upper()
        payload_template = config.get("payload", "{}")
        headers = config.get("headers", {})
        timeout = config.get("timeout", 10)

        if not url:
            logger.warning("WebhookAction: no URL specified.")
            return

        template_context = {
            "document_id": instance.document_id,
            "document_title": instance.document.title,
            "workflow": instance.workflow.label,
            "state": instance.current_state.label if instance.current_state else "",
            "context": instance.context or {},
        }

        try:
            payload_str = jinja2.Template(payload_template).render(**template_context)
        except jinja2.TemplateError:
            logger.exception("WebhookAction: payload template rendering failed.")
            return

        # Validate JSON
        try:
            json.loads(payload_str)
        except (json.JSONDecodeError, ValueError):
            # If not valid JSON, wrap it
            payload_str = json.dumps({"data": payload_str})

        req_headers = {"Content-Type": "application/json"}
        req_headers.update(headers)

        data = payload_str.encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                logger.info(
                    "WebhookAction: %s %s returned %s",
                    method, url, response.status,
                )
        except urllib.error.URLError as e:
            logger.warning("WebhookAction: request to %s failed: %s", url, e)

    def validate_config(self, config):
        errors = []
        if not config.get("url"):
            errors.append("'url' is required.")
        method = config.get("method", "POST").upper()
        if method not in ("POST", "PUT"):
            errors.append("'method' must be POST or PUT.")
        return errors

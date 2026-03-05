"""Action to send an email notification."""

import logging

import jinja2
from django.core.mail import send_mail

from .base import WorkflowAction

logger = logging.getLogger(__name__)


class SendEmailAction(WorkflowAction):
    """
    Send an email notification.

    Config keys:
    - recipient (str): Email address.
    - subject (str): Jinja2 template for subject.
    - body (str): Jinja2 template for body.
    """

    def execute(self, instance, config):
        recipient = config.get("recipient", "")
        subject_template = config.get("subject", "")
        body_template = config.get("body", "")

        if not recipient:
            logger.warning("SendEmailAction: no recipient specified.")
            return

        template_context = {
            "document": instance.document,
            "workflow": instance.workflow,
            "state": instance.current_state,
            "context": instance.context or {},
        }

        try:
            subject = jinja2.Template(subject_template).render(**template_context)
            body = jinja2.Template(body_template).render(**template_context)
        except jinja2.TemplateError:
            logger.exception("SendEmailAction: template rendering failed.")
            return

        send_mail(
            subject=subject,
            message=body,
            from_email=None,  # Use DEFAULT_FROM_EMAIL
            recipient_list=[recipient],
            fail_silently=True,
        )

    def validate_config(self, config):
        errors = []
        if not config.get("recipient"):
            errors.append("'recipient' is required.")
        if not config.get("subject"):
            errors.append("'subject' is required.")
        return errors

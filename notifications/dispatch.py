"""Notification dispatch system — delivers notifications via configured channels."""

import json
import logging
import urllib.request
import urllib.error

from django.core.mail import send_mail
from django.conf import settings

from .constants import (
    ALL_CHANNELS,
    CHANNEL_EMAIL,
    CHANNEL_IN_APP,
    CHANNEL_WEBHOOK,
)

logger = logging.getLogger(__name__)


def send_notification(user, event_type, title, body, document=None):
    """
    Dispatch a notification to a user via all enabled channels.

    Checks user's NotificationPreference for each channel. If no
    preference exists for a channel, defaults to enabled for in_app
    and disabled for email/webhook.
    """
    from .models import Notification, NotificationPreference

    channels = _get_enabled_channels(user, event_type)

    notification = None

    if CHANNEL_IN_APP in channels:
        notification = Notification.objects.create(
            user=user,
            event_type=event_type,
            title=title,
            body=body,
            document=document,
        )
        _push_websocket(user, notification)

    if CHANNEL_EMAIL in channels:
        _send_email(user, title, body)

    if CHANNEL_WEBHOOK in channels:
        webhook_url = _get_webhook_url(user, event_type)
        if webhook_url:
            _send_webhook(webhook_url, event_type, title, body, document)

    return notification


def _get_enabled_channels(user, event_type):
    """Return list of channels enabled for this user + event_type."""
    from .models import NotificationPreference

    prefs = NotificationPreference.objects.filter(
        user=user, event_type=event_type
    )
    pref_map = {p.channel: p.enabled for p in prefs}

    enabled = []
    for channel in ALL_CHANNELS:
        if channel in pref_map:
            if pref_map[channel]:
                enabled.append(channel)
        elif channel == CHANNEL_IN_APP:
            # Default: in_app enabled if no preference set
            enabled.append(channel)

    return enabled


def _get_webhook_url(user, event_type):
    """Get the webhook URL for a user's event_type preference."""
    from .models import NotificationPreference

    try:
        pref = NotificationPreference.objects.get(
            user=user, event_type=event_type, channel=CHANNEL_WEBHOOK
        )
        return pref.webhook_url
    except NotificationPreference.DoesNotExist:
        return None


def _push_websocket(user, notification):
    """Push notification to user via Django Channels WebSocket."""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        group_name = f"user_{user.id}_notifications"
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "notification.send",
                "data": {
                    "id": notification.id,
                    "event_type": notification.event_type,
                    "title": notification.title,
                    "body": notification.body,
                    "document_id": notification.document_id,
                    "created_at": notification.created_at.isoformat(),
                },
            },
        )
    except Exception:
        logger.exception("Failed to push WebSocket notification to user %s", user.id)


def _send_email(user, title, body):
    """Send notification via email."""
    if not user.email:
        return
    try:
        send_mail(
            subject=f"[DocVault] {title}",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL
            if hasattr(settings, "DEFAULT_FROM_EMAIL")
            else "noreply@docvault.local",
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception:
        logger.exception("Failed to send email notification to %s", user.email)


def _send_webhook(url, event_type, title, body, document=None):
    """Send notification via webhook POST."""
    payload = {
        "event_type": event_type,
        "title": title,
        "body": body,
        "document_id": document.id if document else None,
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        logger.exception("Failed to send webhook notification to %s", url)

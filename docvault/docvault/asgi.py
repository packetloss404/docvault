"""ASGI config for DocVault."""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "docvault.settings.production")

django_asgi_app = get_asgi_application()

from processing.consumers import TaskStatusConsumer  # noqa: E402
from notifications.consumers import NotificationConsumer  # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path("ws/status/", TaskStatusConsumer.as_asgi()),
            path("ws/notifications/", NotificationConsumer.as_asgi()),
        ])
    ),
})

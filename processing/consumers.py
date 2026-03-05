"""WebSocket consumers for real-time task status updates."""

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class TaskStatusConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer that streams task progress updates to users."""

    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or self.user.is_anonymous:
            await self.close()
            return

        self.group_name = f"user_{self.user.id}_tasks"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name, self.channel_name,
            )

    async def task_update(self, event):
        """Handle task.update messages from the channel layer."""
        await self.send(text_data=json.dumps(event["data"]))

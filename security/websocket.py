"""WebSocket authentication helpers."""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _get_user_for_token(token_key: str):
    from rest_framework.authtoken.models import Token

    try:
        return Token.objects.select_related("user").get(key=token_key).user
    except Token.DoesNotExist:
        return AnonymousUser()


class TokenAuthMiddleware:
    """Authenticate WebSocket connections with a DRF token query parameter."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        token_values = query.get("token", [])
        if token_values:
            scope = dict(scope)
            scope["user"] = await _get_user_for_token(token_values[0])
        return await self.inner(scope, receive, send)

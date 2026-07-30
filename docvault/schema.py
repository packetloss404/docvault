"""OpenAPI schema helpers for DocVault."""

from drf_spectacular.openapi import AutoSchema
from drf_spectacular.plumbing import build_serializer_context
from rest_framework import serializers
from rest_framework.generics import GenericAPIView
from rest_framework.views import APIView


class EmptySerializer(serializers.Serializer):
    """Fallback serializer for response-only APIViews."""


class DocVaultAutoSchema(AutoSchema):
    """DocVault schema class with a safe fallback for plain APIViews."""

    def _get_serializer(self):
        view = self.view
        if isinstance(view, APIView) and not isinstance(view, GenericAPIView):
            has_serializer = any(
                (
                    callable(getattr(view, "get_serializer", None)),
                    callable(getattr(view, "get_serializer_class", None)),
                    hasattr(view, "serializer_class"),
                )
            )
            if not has_serializer:
                return EmptySerializer(context=build_serializer_context(view))
        return super()._get_serializer()

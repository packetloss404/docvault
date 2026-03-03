"""Core middleware for DocVault."""

import threading

from django.utils.deprecation import MiddlewareMixin

_thread_locals = threading.local()


def get_current_user():
    """Get the current user from thread-local storage."""
    return getattr(_thread_locals, "user", None)


class CurrentUserMiddleware(MiddlewareMixin):
    """
    Stores the current authenticated user in thread-local storage
    so that AuditableModel can automatically set created_by/updated_by.
    """

    def process_request(self, request):
        _thread_locals.user = getattr(request, "user", None)

    def process_response(self, request, response):
        _thread_locals.user = None
        return response

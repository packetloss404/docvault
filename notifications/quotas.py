"""Quota enforcement logic."""

import logging

from django.db.models import Sum

from documents.models import Document, DocumentFile

logger = logging.getLogger(__name__)


def get_effective_quota(user):
    """
    Return the effective quota for a user.

    Priority: user-specific > group > global.
    Returns a Quota instance or None if no quota applies.
    """
    from .models import Quota

    # 1. User-specific quota
    user_quota = Quota.objects.filter(user=user).first()
    if user_quota:
        return user_quota

    # 2. Group-based quota (first matching group)
    user_groups = user.groups.all()
    if user_groups.exists():
        group_quota = Quota.objects.filter(
            group__in=user_groups, user__isnull=True
        ).first()
        if group_quota:
            return group_quota

    # 3. Global quota (no user, no group)
    global_quota = Quota.objects.filter(
        user__isnull=True, group__isnull=True
    ).first()
    return global_quota


def get_usage(user):
    """Return current document count and storage usage for a user."""
    document_count = Document.objects.filter(owner=user).count()
    storage_result = DocumentFile.objects.filter(
        document__owner=user
    ).aggregate(total=Sum("size"))
    storage_bytes = storage_result["total"] or 0
    return document_count, storage_bytes


def check_quota(user):
    """
    Check whether the user is within their quota.

    Returns (allowed, message) tuple.
    """
    quota = get_effective_quota(user)
    if not quota:
        return True, "No quota configured."

    doc_count, storage_bytes = get_usage(user)

    if quota.max_documents is not None and doc_count >= quota.max_documents:
        return False, (
            f"Document limit reached: {doc_count}/{quota.max_documents} documents."
        )

    if quota.max_storage_bytes is not None and storage_bytes >= quota.max_storage_bytes:
        used_mb = storage_bytes / (1024 * 1024)
        limit_mb = quota.max_storage_bytes / (1024 * 1024)
        return False, (
            f"Storage limit reached: {used_mb:.1f}MB / {limit_mb:.1f}MB."
        )

    return True, "Within quota."


def get_quota_usage_data(user):
    """Return full quota usage data for API response."""
    quota = get_effective_quota(user)
    doc_count, storage_bytes = get_usage(user)

    max_documents = quota.max_documents if quota else None
    max_storage_bytes = quota.max_storage_bytes if quota else None

    documents_remaining = None
    if max_documents is not None:
        documents_remaining = max(0, max_documents - doc_count)

    storage_remaining = None
    if max_storage_bytes is not None:
        storage_remaining = max(0, max_storage_bytes - storage_bytes)

    return {
        "document_count": doc_count,
        "storage_bytes": storage_bytes,
        "max_documents": max_documents,
        "max_storage_bytes": max_storage_bytes,
        "documents_remaining": documents_remaining,
        "storage_remaining": storage_remaining,
    }

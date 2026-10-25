"""Shared preservation guard for APIs and automated document mutations."""

from rest_framework.exceptions import APIException


class LegalHoldConflict(APIException):
    status_code = 409
    default_detail = "This document is under legal hold. Modifications and deletion are restricted."
    default_code = "legal_hold_conflict"


def ensure_document_mutable(document, user=None):
    if document.is_held and not (user and user.has_perm("legal_hold.override_hold")):
        raise LegalHoldConflict()

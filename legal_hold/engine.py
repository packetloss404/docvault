"""Hold lifecycle engine for the legal_hold module.

Provides functions to activate, release, and refresh legal holds.
All hold state transitions and document capture logic lives here.
"""

import logging

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .constants import (
    ACTIVE,
    CABINET,
    CUSTODIAN,
    DATE_RANGE,
    DOCUMENT_TYPE,
    RELEASED,
    SEARCH_QUERY,
    SPECIFIC_DOCUMENTS,
    TAG,
)

logger = logging.getLogger(__name__)


def evaluate_criteria(hold):
    """
    Evaluate all criteria attached to a hold and return matching document IDs.

    Each criterion produces a filter on the Document queryset. Multiple
    criteria are combined with AND logic (intersection).

    Returns:
        list[int]: Primary keys of matching documents.
    """
    from documents.models import Document

    qs = Document.objects.all()
    criteria_list = hold.criteria.all()

    if not criteria_list.exists():
        return []

    for criterion in criteria_list:
        ct = criterion.criteria_type
        value = criterion.value

        if ct == CUSTODIAN:
            user_ids = value.get("user_ids", [])
            qs = qs.filter(
                Q(owner_id__in=user_ids) | Q(created_by_id__in=user_ids)
            )
        elif ct == DATE_RANGE:
            start = value.get("start")
            end = value.get("end")
            if start and end:
                qs = qs.filter(created__range=(start, end))
        elif ct == TAG:
            tag_ids = value.get("tag_ids", [])
            qs = qs.filter(tags__id__in=tag_ids)
        elif ct == DOCUMENT_TYPE:
            type_ids = value.get("type_ids", [])
            qs = qs.filter(document_type_id__in=type_ids)
        elif ct == SEARCH_QUERY:
            query = value.get("query", "")
            if query:
                qs = qs.filter(content__icontains=query)
        elif ct == CABINET:
            cabinet_ids = value.get("cabinet_ids", [])
            qs = qs.filter(cabinet_id__in=cabinet_ids)
        elif ct == SPECIFIC_DOCUMENTS:
            document_ids = value.get("document_ids", [])
            qs = qs.filter(pk__in=document_ids)
        else:
            logger.warning(
                "Unknown criteria type %r on hold %s", ct, hold.pk
            )

    return list(qs.distinct().values_list("pk", flat=True))


@transaction.atomic
def activate_hold(hold):
    """
    Activate a legal hold.

    1. Evaluate criteria to find matching documents.
    2. Create LegalHoldDocument records for each match.
    3. Set Document.is_held=True on all matched documents.
    4. Update hold status to ACTIVE with activation timestamp.
    5. Trigger custodian notification tasks.

    Args:
        hold: LegalHold instance in DRAFT status.

    Returns:
        int: Number of documents placed on hold.
    """
    from documents.models import Document

    from .models import LegalHoldDocument

    document_ids = evaluate_criteria(hold)

    # Create hold-document junction records (skip duplicates)
    existing_ids = set(
        hold.held_documents.values_list("document_id", flat=True)
    )
    new_ids = [did for did in document_ids if did not in existing_ids]

    LegalHoldDocument.objects.bulk_create(
        [
            LegalHoldDocument(hold=hold, document_id=did)
            for did in new_ids
        ],
        ignore_conflicts=True,
    )

    # Mark documents as held
    Document.objects.filter(pk__in=document_ids).update(is_held=True)

    # Transition hold to ACTIVE
    hold.status = ACTIVE
    hold.activated_at = timezone.now()
    hold.save(update_fields=["status", "activated_at", "updated_at"])

    # Trigger custodian notification (async)
    from .tasks import notify_custodians

    notify_custodians.delay(hold.pk)

    logger.info(
        "Activated hold %s (%s): %d documents captured",
        hold.pk,
        hold.name,
        len(document_ids),
    )
    return len(document_ids)


@transaction.atomic
def release_hold(hold, user, reason=""):
    """
    Release a legal hold.

    1. Set hold status to RELEASED with release metadata.
    2. Set released_at on all LegalHoldDocument records.
    3. For each document, check if any other active hold applies --
       if not, clear the is_held flag.

    Args:
        hold: LegalHold instance in ACTIVE status.
        user: The user performing the release.
        reason: Reason for releasing the hold.
    """
    from documents.models import Document

    from .models import LegalHoldDocument

    now = timezone.now()

    # Transition hold to RELEASED
    hold.status = RELEASED
    hold.released_at = now
    hold.released_by = user
    hold.release_reason = reason
    hold.save(
        update_fields=[
            "status",
            "released_at",
            "released_by",
            "release_reason",
            "updated_at",
        ]
    )

    # Mark all held documents as released
    hold.held_documents.filter(released_at__isnull=True).update(
        released_at=now
    )

    # For each document on this hold, check if it is still held by
    # another active hold. If not, clear the is_held flag.
    held_doc_ids = list(
        hold.held_documents.values_list("document_id", flat=True)
    )

    still_held_ids = set(
        LegalHoldDocument.objects.filter(
            document_id__in=held_doc_ids,
            hold__status=ACTIVE,
            released_at__isnull=True,
        )
        .exclude(hold=hold)
        .values_list("document_id", flat=True)
    )

    release_ids = [did for did in held_doc_ids if did not in still_held_ids]
    Document.objects.filter(pk__in=release_ids).update(is_held=False)

    logger.info(
        "Released hold %s (%s): %d documents freed, %d still held by other holds",
        hold.pk,
        hold.name,
        len(release_ids),
        len(still_held_ids),
    )


@transaction.atomic
def refresh_hold(hold):
    """
    Re-evaluate criteria for an active hold and add new matches.

    Existing held documents are preserved; only new matches are added.

    Args:
        hold: LegalHold instance in ACTIVE status.

    Returns:
        int: Number of newly added documents.
    """
    from documents.models import Document

    from .models import LegalHoldDocument

    document_ids = evaluate_criteria(hold)

    existing_ids = set(
        hold.held_documents.values_list("document_id", flat=True)
    )
    new_ids = [did for did in document_ids if did not in existing_ids]

    if new_ids:
        LegalHoldDocument.objects.bulk_create(
            [
                LegalHoldDocument(hold=hold, document_id=did)
                for did in new_ids
            ],
            ignore_conflicts=True,
        )
        Document.objects.filter(pk__in=new_ids).update(is_held=True)

    logger.info(
        "Refreshed hold %s (%s): %d new documents added",
        hold.pk,
        hold.name,
        len(new_ids),
    )
    return len(new_ids)

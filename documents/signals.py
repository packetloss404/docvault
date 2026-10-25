"""Django signals for the documents app."""

from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from .models import Document


@receiver(post_save, sender=Document)
def index_document_on_save(sender, instance, **kwargs):
    from search.tasks import index_document_task

    transaction.on_commit(lambda pk=instance.pk: index_document_task.delay(pk))


@receiver(post_delete, sender=Document)
def remove_document_on_delete(sender, instance, **kwargs):
    from search.tasks import remove_document_task

    transaction.on_commit(lambda pk=instance.pk: remove_document_task.delay(pk))


@receiver(m2m_changed, sender=Document.tags.through)
def index_document_on_tag_change(sender, instance, action, reverse, pk_set, **kwargs):
    if action not in {"post_add", "post_remove", "post_clear"}:
        return
    from search.tasks import index_document_task

    if reverse:
        # Reverse clear has no remaining relation from which to recover IDs.
        document_ids = pk_set if pk_set is not None else Document.objects.values_list("pk", flat=True)
    else:
        document_ids = [instance.pk]
    for document_id in document_ids:
        transaction.on_commit(lambda pk=document_id: index_document_task.delay(pk))

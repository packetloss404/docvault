"""Django signals for the documents app."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Document


@receiver(post_save, sender=Document)
def index_document_on_save(sender, instance, **kwargs):
    from search.tasks import index_document_task

    index_document_task.delay(instance.pk)


@receiver(post_delete, sender=Document)
def remove_document_on_delete(sender, instance, **kwargs):
    from search.tasks import remove_document_task

    remove_document_task.delay(instance.pk)

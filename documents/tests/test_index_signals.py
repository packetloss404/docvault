import pytest
from django.db import transaction

from documents.models import Document


@pytest.mark.django_db(transaction=True)
def test_index_signals_publish_after_commit_and_keep_deleted_primary_key(monkeypatch):
    indexed = []
    removed = []
    monkeypatch.setattr('search.tasks.index_document_task.delay', indexed.append)
    monkeypatch.setattr('search.tasks.remove_document_task.delay', removed.append)
    with transaction.atomic():
        document = Document.objects.create(title='Committed document')
        primary_key = document.pk
        assert indexed == []
    assert indexed == [primary_key]
    with transaction.atomic():
        document.delete()
        assert removed == []
        assert document.pk is None
    assert removed == [primary_key]


@pytest.mark.django_db(transaction=True)
def test_rolled_back_metadata_never_reaches_index_worker(monkeypatch):
    indexed = []
    monkeypatch.setattr('search.tasks.index_document_task.delay', indexed.append)
    with pytest.raises(ValueError), transaction.atomic():
        Document.objects.create(title='Rolled back document')
        raise ValueError('Abort')
    assert indexed == []

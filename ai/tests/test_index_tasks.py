from types import SimpleNamespace

import pytest

from ai.tasks import rebuild_vector_index, update_vector_index
from ai.vector_store import get_vector_store, reset_vector_store
from documents.models import Document


@pytest.mark.django_db
def test_rebuild_iterates_prefetched_documents_and_publishes_a_snapshot(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = tmp_path
    settings.EMBEDDING_DIM = 3
    settings.LLM_ENABLED = True
    reset_vector_store()
    document = Document.objects.create(title='Rebuild', content='Actual queryset with prefetched tags')
    client = SimpleNamespace(embedding_dimension=3, count_tokens=lambda text: len(text.split()),
                             embed_batch=lambda texts: [[1.0, 0.0, 0.0] for text in texts])
    monkeypatch.setattr('ai.client.get_llm_client', lambda: client)
    monkeypatch.setattr('ai.embeddings.get_llm_client', lambda: client)
    try:
        result = rebuild_vector_index.run()
        assert result['indexed'] == 1
        assert get_vector_store().doc_ids == [document.pk]
    finally:
        reset_vector_store()


@pytest.mark.django_db
def test_incremental_index_iterates_prefetched_documents(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = tmp_path
    settings.EMBEDDING_DIM = 3
    settings.LLM_ENABLED = True
    reset_vector_store()
    document = Document.objects.create(title='Incremental', content='Actual prefetched queryset')
    monkeypatch.setattr('ai.embeddings.generate_document_embedding', lambda document: [0.0, 1.0, 0.0])
    try:
        result = update_vector_index.run()
        assert result['added'] == 1
        assert get_vector_store().doc_ids == [document.pk]
    finally:
        reset_vector_store()

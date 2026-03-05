"""Document Q&A via Retrieval-Augmented Generation (RAG)."""

import logging

from .client import get_llm_client
from .constants import MAX_CHAT_HISTORY, RAG_TOP_K
from .embeddings import chunk_text, generate_query_embedding
from .vector_store import get_vector_store

logger = logging.getLogger(__name__)


def chat_with_document(document_id: int, question: str, history: list[dict] | None = None) -> dict:
    """Ask a question about a specific document.

    Args:
        document_id: The document to query.
        question: The user's question.
        history: Optional conversation history [{role, content}, ...].

    Returns:
        Dict with 'answer' and 'sources' keys.
    """
    client = get_llm_client()
    if not client:
        return {"answer": "AI features are not enabled.", "sources": []}

    from documents.models import Document

    try:
        document = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        return {"answer": "Document not found.", "sources": []}

    content = document.content or ""
    if not content.strip():
        return {"answer": "This document has no text content to query.", "sources": []}

    # Build context from document chunks
    chunks = chunk_text(content, chunk_size=500, overlap=50)
    if not chunks:
        return {"answer": "Document content is too short to process.", "sources": []}

    # Find the most relevant chunks for the question
    query_embedding = generate_query_embedding(question)
    if query_embedding is not None:
        chunk_scores = []
        for i, chunk in enumerate(chunks):
            chunk_embedding = client.embed(chunk)
            # Cosine similarity via dot product of normalized vectors
            import numpy as np

            q = np.array(query_embedding)
            c = np.array(chunk_embedding)
            q_norm = q / (np.linalg.norm(q) or 1)
            c_norm = c / (np.linalg.norm(c) or 1)
            similarity = float(np.dot(q_norm, c_norm))
            chunk_scores.append((i, chunk, similarity))

        chunk_scores.sort(key=lambda x: x[2], reverse=True)
        relevant_chunks = [cs[1] for cs in chunk_scores[:RAG_TOP_K]]
    else:
        # Fallback: use first chunks
        relevant_chunks = chunks[:RAG_TOP_K]

    context_text = "\n\n---\n\n".join(relevant_chunks)

    # Build prompt with history
    history_text = ""
    if history:
        recent = history[-MAX_CHAT_HISTORY:]
        for msg in recent:
            role = msg.get("role", "user")
            history_text += f"\n{role.capitalize()}: {msg['content']}"

    prompt = (
        f"You are a helpful document assistant. Answer the question based ONLY on the "
        f"provided document context. If the answer is not in the context, say so.\n"
        f"\nDocument: {document.title}"
    )
    if history_text:
        prompt += f"\n\nConversation history:{history_text}"
    prompt += f"\n\nQuestion: {question}"

    answer = client.generate(prompt, context=context_text)

    return {
        "answer": answer,
        "sources": [{
            "document_id": document_id,
            "title": document.title,
            "chunk_count": len(relevant_chunks),
        }],
    }


def chat_across_documents(question: str, user_id: int | None = None, history: list[dict] | None = None) -> dict:
    """Ask a question across all documents using RAG.

    1. Embed the question.
    2. Find relevant document chunks via FAISS.
    3. Send chunks + question to LLM.
    4. Return answer with source references.
    """
    client = get_llm_client()
    if not client:
        return {"answer": "AI features are not enabled.", "sources": []}

    query_embedding = generate_query_embedding(question)
    if query_embedding is None:
        return {"answer": "Could not generate query embedding.", "sources": []}

    # Find relevant documents
    store = get_vector_store()
    raw_results = store.search(query_embedding, k=RAG_TOP_K)

    if not raw_results:
        return {"answer": "No relevant documents found.", "sources": []}

    from documents.models import Document

    doc_ids = [doc_id for doc_id, _ in raw_results]

    qs = Document.objects.filter(pk__in=doc_ids)
    if user_id:
        qs = qs.filter(owner_id=user_id)

    documents = {doc.pk: doc for doc in qs}

    # Build context from relevant documents
    context_parts = []
    sources = []
    for doc_id, score in raw_results:
        if doc_id not in documents:
            continue
        doc = documents[doc_id]
        content = doc.content or ""
        # Truncate each document's content
        max_per_doc = 2000
        if len(content) > max_per_doc:
            content = content[:max_per_doc] + "..."

        context_parts.append(f"[Document: {doc.title} (ID: {doc.pk})]\n{content}")
        sources.append({
            "document_id": doc.pk,
            "title": doc.title,
            "score": score,
        })

    context_text = "\n\n---\n\n".join(context_parts)

    # Build prompt
    history_text = ""
    if history:
        recent = history[-MAX_CHAT_HISTORY:]
        for msg in recent:
            role = msg.get("role", "user")
            history_text += f"\n{role.capitalize()}: {msg['content']}"

    prompt = (
        "You are a helpful document management assistant. Answer the question based on the "
        "provided document contexts. Reference specific documents by title when relevant. "
        "If the answer is not in the provided contexts, say so."
    )
    if history_text:
        prompt += f"\n\nConversation history:{history_text}"
    prompt += f"\n\nQuestion: {question}"

    answer = client.generate(prompt, context=context_text)

    return {
        "answer": answer,
        "sources": sources,
    }

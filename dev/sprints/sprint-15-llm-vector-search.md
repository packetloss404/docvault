# Sprint 15: LLM Integration & Vector Search

## Phase: 5 - Intelligence & AI
## Duration: 2 weeks
## Prerequisites: Sprint 14 (Barcode Detection & ASN System)

---

## Sprint Goal
Integrate LLM capabilities (OpenAI, Ollama) for document Q&A, AI-powered classification, and content summarization. Build FAISS vector search for semantic document similarity and "more like this" features.

---

## Context for Agents

### Read Before Starting
- `/doc/product-spec.md` - Section 2.9 (ML/AI Module - LLM Integration)
- `/doc/research/paperless-ngx-analysis.md` - Section 15 (LLM & Vector Search)
- `/doc/architecture.md` - Section 7 (Dual Search Strategy)

---

## Tasks

### Task 15.1: LLM Client Abstraction
- LLMClient ABC with `generate(prompt, context)` and `embed(text)` methods
- OpenAI implementation (via openai Python package)
- Ollama implementation (via ollama Python package, local LLM)
- Azure AI implementation (optional)
- Configuration via environment variables:
  - `LLM_ENABLED`, `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_API_ENDPOINT`
  - `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`
- Retry logic and timeout handling
- Token counting and budget management

### Task 15.2: Document Embedding & FAISS Index
- Embedding generation for documents (combine title + metadata + content)
- Text chunking via TokenTextSplitter (for large documents)
- FAISS index management: create, add, remove, rebuild
- Index persistence to disk
- Celery task: update vector index (daily at 3 AM)
- Celery task: rebuild vector index (on-demand)
- AIPlugin (order 110) for processing pipeline: generate embedding on consume

### Task 15.3: Semantic Search API
- GET `/api/v1/search/semantic/?query=...` - Natural language search via embeddings
- GET `/api/v1/search/similar/{id}/` - Enhanced "more like this" using vector similarity
- Hybrid search: combine keyword (Elasticsearch) + semantic (FAISS) results
- Configurable result weighting between keyword and semantic

### Task 15.4: Document Q&A (Chat)
- POST `/api/v1/documents/{id}/chat/` - Ask questions about a document
- POST `/api/v1/chat/` - Ask questions across all documents (RAG)
- Retrieval-Augmented Generation:
  1. Embed user query
  2. Find relevant document chunks via FAISS
  3. Send chunks + query to LLM
  4. Return LLM response with source references
- Conversation history support (session-based)
- Rate limiting per user

### Task 15.5: AI-Powered Features
- AI classification: LLM-based document type/correspondent suggestion
- Content summarization: generate document summary on demand
- Entity extraction: extract dates, amounts, names, addresses from content
- Smart title generation: suggest better titles based on content
- Store AI-generated metadata as custom field values

### Task 15.6: Frontend AI Features
- "Similar documents" section on document detail (from FAISS)
- Document chat interface (sidebar panel or modal)
- AI suggestion indicators (separate from ML suggestions)
- "Summarize" button on document detail
- AI configuration page (admin): provider, model, API key
- AI usage statistics dashboard

---

## Dependencies

### New Python Packages
```
openai>=1.0
ollama>=0.6
faiss-cpu>=1.10
llama-index-core>=0.14
sentence-transformers>=3.0
tiktoken>=0.7
```

---

## Definition of Done
- [ ] LLM client works with OpenAI and Ollama
- [ ] Document embeddings generated and stored in FAISS
- [ ] Semantic search returns relevant results
- [ ] "More like this" uses vector similarity
- [ ] Document Q&A works (RAG pipeline)
- [ ] Content summarization generates useful summaries
- [ ] AI configuration via environment variables works
- [ ] Frontend shows similar documents and chat interface
- [ ] All features have unit tests
- [ ] AI features gracefully degrade when LLM not configured

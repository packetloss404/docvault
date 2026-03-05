# DocVault - Project Plan

### Version: 1.0 Draft
### Last Updated: 2026-03-01

---

## Overview

The DocVault project is divided into **6 phases**, each building on the previous. Each phase contains **2-4 sprints** of manageable scope. Each sprint has its own detailed document in `/doc/sprints/` that agents should read before executing sprint tasks.

**Sprint Duration**: 2 weeks (10 working days)
**Total Sprints**: 22
**Total Phases**: 7

---

## Phase Summary

| Phase | Name | Sprints | Focus |
|-------|------|---------|-------|
| 1 | Foundation | 1-3 | Project scaffolding, core models, basic API, auth |
| 2 | Document Processing | 4-6 | Processing pipeline, OCR, parsers, storage |
| 3 | Organization & Search | 7-9 | Tags, cabinets, custom fields, Elasticsearch, saved views |
| 4 | Workflow & Automation | 10-12 | Workflow engine, rules, retention, notifications |
| 5 | Intelligence & AI | 13-15 | ML classification, barcode detection, LLM, vector search |
| 6 | Collaboration & Polish | 16-18 | Sharing, comments, UI polish, deployment, docs |
| 7 | Advanced Features | 19-22 | Zone OCR, NER, search analytics, e-signatures, legal hold, annotations, physical records |

---

## Phase 1: Foundation (Sprints 1-3)

### Goal
Establish the project foundation: Django project structure, core models, authentication, basic API, and frontend scaffold.

### Sprint 1: Project Scaffolding & Core Models
- Django project initialization with modular structure
- Core base models (SoftDeleteModel, AuditableModel, OwnedModel)
- Document model, DocumentType, DocumentFile, DocumentVersion
- PostgreSQL database setup with migrations
- Docker Compose for development environment
- Basic Django admin for data inspection
- Environment-based settings management

### Sprint 2: Authentication & Permissions
- Django auth + django-allauth setup
- LDAP authentication backend (django-auth-ldap)
- Token authentication for API
- Role and Permission models
- Object-level ACLs (django-guardian integration)
- User and group management API
- Basic middleware stack (CORS, security headers)
- Login/registration API endpoints

### Sprint 3: REST API Foundation & Frontend Scaffold
- DRF configuration (pagination, filtering, throttling)
- Document CRUD ViewSets with permission checking
- DocumentType ViewSets
- OpenAPI schema generation (drf-spectacular)
- Angular project initialization (Angular 21+)
- Angular routing, auth guard, HTTP interceptors
- Login page, basic layout with navigation
- Docker multi-stage build for frontend

---

## Phase 2: Document Processing (Sprints 4-6)

### Goal
Build the complete document processing pipeline: file upload, parser system, OCR, text extraction, thumbnail generation, and storage backends.

### Sprint 4: Storage & Upload Pipeline
- Storage backend abstraction (local, S3-compatible)
- MinIO integration for S3 storage
- File upload endpoint with progress tracking
- Document consumer orchestrator (ProcessingPipeline)
- ProcessingPlugin base class and plugin registry
- PreflightPlugin (MIME detection, duplicate check, validation)
- Celery + Redis setup for async processing
- Task status tracking (PaperlessTask model)
- WebSocket setup for progress notifications

### Sprint 5: Parsers & OCR
- Parser base class and registry
- PDFParser (OCRmyPDF integration)
- ImageParser (OCRmyPDF + ImageMagick)
- OfficeParser (Tika/LibreOffice conversion)
- TextParser (plain text, HTML)
- EmailParser (EML/MSG with attachment extraction)
- ArchiveParser (ZIP extraction with recursive processing)
- OCR configuration (language, mode, DPI, deskew, rotation)
- Text extraction and normalization
- Language detection (langdetect)
- Date extraction from content

### Sprint 6: Thumbnails, Versions & Non-Destructive Mode
- Thumbnail generation plugin (first page preview, WebP format)
- Document versioning (create, list, activate, compare)
- DocumentPage model for page-level content
- Non-destructive storage mode (keep originals untouched)
- Archive file generation (searchable PDF/A)
- Checksum calculation (MD5 + SHA-256)
- Pre/post-consume hook plugin (user scripts)
- Document detail frontend page (preview, metadata, content tabs)
- File download endpoint (original + archive)

---

## Phase 3: Organization & Search (Sprints 7-9)

### Goal
Build the complete organization system (tags, cabinets, custom fields) and search infrastructure (Elasticsearch, saved views, frontend search UI).

### Sprint 7: Tags, Correspondents & Cabinets
- Tag model (MPTT hierarchical, 5-level, color-coded)
- Correspondent model with matching algorithms
- Cabinet model (MPTT hierarchical, unlimited nesting)
- StoragePath model with Jinja2 templates
- Matching algorithm implementation (NONE, ANY, ALL, LITERAL, REGEX, FUZZY)
- Tag/Correspondent/Cabinet CRUD API
- Tag autocomplete endpoint
- Frontend: Tag management page, cabinet tree view
- Bulk tag/correspondent assignment API

### Sprint 8: Custom Fields & Metadata
- CustomField model (12 data types)
- CustomFieldInstance model (per-document values)
- MetadataType model with validators, parsers, lookups
- Custom field CRUD API
- Per-document-type field/metadata assignment
- Custom field filtering in document list API
- Custom field query parser (JSON-based complex queries)
- Frontend: Custom field editor in document detail
- Frontend: Metadata editor in document detail

### Sprint 9: Search & Saved Views
- Elasticsearch integration (index schema, CRUD operations)
- Full-text search with relevance ranking
- Faceted search (date, type, tags, correspondent, custom fields)
- Search highlighting
- Permission-aware search filtering
- Search autocomplete endpoint
- Saved View model (display mode, columns, filters, sort)
- Saved View CRUD API
- Frontend: Global search (Ctrl+K) with typeahead
- Frontend: Document list with three display modes (table, cards)
- Frontend: Advanced filter builder
- Frontend: Saved view sidebar + dashboard widgets

---

## Phase 4: Workflow & Automation (Sprints 10-12)

### Goal
Build the workflow engine (state machines + trigger/action rules), retention policies, document sources, and notification system.

### Sprint 10: Workflow State Machine
- WorkflowTemplate model
- WorkflowState model (initial, intermediate, final, completion %)
- WorkflowTransition model (conditional, with Python expression evaluation)
- WorkflowStateAction model (on_entry, on_exit)
- WorkflowStateEscalation model (timeout-based auto-transition)
- WorkflowTransitionField model (custom form fields)
- WorkflowInstance model (per-document runtime)
- WorkflowInstanceLogEntry model (audit trail)
- Workflow engine (state machine execution, condition evaluation)
- Built-in actions: set metadata, add tag, add to cabinet, modify properties
- Workflow CRUD API
- Celery tasks for escalation processing

### Sprint 11: Trigger-Action Rules & Sources
- WorkflowRule model (triggers + actions)
- Trigger types: CONSUMPTION, DOCUMENT_ADDED, DOCUMENT_UPDATED, SCHEDULED
- Action types: tag, correspondent, type, storage path, custom field, permissions
- Email action (WorkflowActionEmail with placeholders)
- Webhook action (WorkflowActionWebhook with headers, body)
- Watch folder source backend
- Email source backend (IMAP + OAuth2 for Gmail/Outlook)
- Staging folder source backend
- S3 source backend
- Source CRUD API
- Celery tasks for mail fetching and folder watching
- Frontend: Source configuration pages

### Sprint 12: Retention, Quotas & Notifications
- Retention policy fields on DocumentType (auto-trash, auto-delete)
- Retention enforcement Celery task
- Stub pruning for incomplete uploads
- Usage quota model (per-user, per-group document/storage limits)
- Quota enforcement on upload
- Notification model and preferences
- In-app notifications via WebSocket
- Email notification channel (SMTP configuration)
- Webhook notification channel
- Notification trigger configuration
- Frontend: Notification bell + preferences
- Frontend: Retention policy configuration in document type editor

---

## Phase 5: Intelligence & AI (Sprints 13-15)

### Goal
Build ML-powered classification, barcode detection, LLM integration, and semantic search.

### Sprint 13: ML Classification Pipeline
- DocumentClassifier class (scikit-learn)
- Four classifiers: tags, correspondent, document type, storage path
- Feature extraction: TF-IDF with 1-2 ngrams
- Training pipeline: collect MATCH_AUTO documents, vectorize, fit
- Prediction pipeline: vectorize new document, predict
- Confidence scoring
- Smart retraining (hash-based change detection)
- Redis-backed stemming cache
- Content preprocessing (tokenization, stemming, stop words)
- ClassificationPlugin for processing pipeline
- Classifier training Celery task (hourly schedule)
- Suggestions API endpoint
- Frontend: Suggestion chips on document detail page
- Frontend: "Accept suggestion" one-click actions

### Sprint 14: Barcode Detection & ASN System
- Barcode detection plugin (zxing-cpp)
- Separator barcode support (split multi-document scans)
- ASN barcode extraction (prefix matching)
- Tag barcode extraction (regex mapping, auto-creation)
- ASN management (auto-assign, uniqueness, display)
- Barcode configuration (DPI, upscaling, max pages, formats)
- Frontend: ASN display and search
- Frontend: Barcode configuration in admin

### Sprint 15: LLM Integration & Vector Search
- LLM client abstraction (OpenAI, Ollama, Azure)
- Document embedding generation (HuggingFace/OpenAI)
- FAISS vector index management
- Semantic search endpoint ("more like this")
- Document Q&A (chat with your documents)
- AI-powered classification (LLM-based suggestions)
- Content summarization
- Entity extraction
- Vector index update Celery task
- Frontend: "Similar documents" section
- Frontend: Document chat interface
- Frontend: AI configuration in admin
- LLM provider configuration (API keys, models, endpoints)

---

## Phase 6: Collaboration & Polish (Sprints 16-18)

### Goal
Build collaboration features, enterprise security hardening, UI polish, deployment tooling, and documentation.

### Sprint 16: Collaboration Features
- Document comments/notes model (per-user, timestamped, markdown)
- Check-in/check-out model (exclusive lock, expiration, forced release)
- Share link model (slug, expiration, optional password)
- Share bundle model (multiple documents)
- Comments CRUD API
- Check-in/check-out API
- Share link CRUD API + public access endpoint
- Activity feed per document
- Frontend: Notes tab in document detail
- Frontend: Share dialog with link generation
- Frontend: Check-out/check-in buttons with status indicator
- Frontend: Activity timeline

### Sprint 17: Security Hardening & Enterprise Features
- AES-256-CBC storage encryption backend
- Encrypted storage configuration
- Document signing (GPG/PGP integration)
- OpenID Connect authentication backend
- Two-factor OTP authentication (TOTP/HOTP)
- Scanner source backend (SANE integration)
- Compressed archive source backend
- Audit log viewer API
- IP-based access control (optional)
- CSRF/XSS hardening
- Security headers middleware
- Frontend: Audit log viewer
- Frontend: Two-factor setup page
- Frontend: Encrypted storage configuration

### Sprint 18: UI Polish, Deployment & Documentation
- Dashboard with drag-and-drop widgets
- Dark mode and theming support
- Multi-language support (i18n framework + initial translations)
- Workflow designer (visual state machine builder)
- Bulk operations UI (multi-select, bulk edit, bulk download)
- Admin panel polishing
- Kubernetes Helm chart
- Production Docker image optimization
- Health check endpoints (/health, /ready, /metrics)
- Prometheus metrics integration
- Structured JSON logging
- User documentation (getting started, configuration, API reference)
- Developer documentation (plugin development, contributing guide)
- Comprehensive README.md
- Performance testing and optimization
- Security audit checklist

---

## Phase 7: Advanced Features (Sprints 19-22)

### Goal
Implement high-value features identified from extended market analysis of 45+ DMS systems. These features fill significant gaps and differentiate DocVault from competitors.

### Sprint 19: Zone OCR, NER & Search Analytics
- Zone OCR / Form Template Recognition (visual zone designer, template matching, structured extraction)
- Named Entity Recognition as search facets (persons, orgs, locations, dates, amounts)
- NER processing plugin (order 115, after AI plugin)
- Entity indexing in Elasticsearch as structured facets
- Search analytics dashboard (top queries, zero-result queries, click-through rates)
- Synonym management UI for admin
- Search curations (pin/hide results)
- Entity co-occurrence graph visualization

### Sprint 20: Document Relationships & Contributor Portal
- DocumentRelationship model with typed, bidirectional links
- Built-in relationship types (supersedes, references, responds-to, contradicts, etc.)
- Custom relationship types
- Relationship panel and graph visualization on document detail
- Document request workflow (request specific docs from external parties with deadline)
- Guest upload links (tokenized URLs, no account needed)
- Contributor portal with branding and metadata forms
- Review queue for submitted documents

### Sprint 21: E-Signatures & Visual Annotations
- E-Signature flow with external signer support
- Drag-and-drop signature field placement on PDFs
- Tokenized email links for external signers
- Signer identity verification (email, SMS, IP logging)
- Certificate of completion PDF generation
- RFC 3161 qualified timestamps
- Visual page-level annotation overlay (non-destructive)
- Annotation types: highlight, underline, sticky note, freehand draw, rectangle, text box, rubber stamp
- Annotation permissions and author tracking
- Export annotated PDF
- W3C Web Annotation standard compliance

### Sprint 22: Legal Hold, Content-Addressable Storage & Physical Records
- Legal hold with custodian management
- Hold placement (freeze documents matching criteria)
- Custodian notification and acknowledgement tracking
- Content-addressable storage backend (SHA-256 blob store)
- Automatic binary deduplication
- Storage savings reporting
- Physical records management (PhysicalLocation model, charge-out register)
- Barcode-driven physical checkout
- Destruction certificate generation

---

## Sprint Document Reference

Each sprint has a detailed document in `/doc/sprints/`:

| Sprint | File | Phase |
|--------|------|-------|
| 1 | `/doc/sprints/sprint-01-scaffolding.md` | Foundation |
| 2 | `/doc/sprints/sprint-02-auth-permissions.md` | Foundation |
| 3 | `/doc/sprints/sprint-03-api-frontend.md` | Foundation |
| 4 | `/doc/sprints/sprint-04-storage-upload.md` | Processing |
| 5 | `/doc/sprints/sprint-05-parsers-ocr.md` | Processing |
| 6 | `/doc/sprints/sprint-06-thumbnails-versions.md` | Processing |
| 7 | `/doc/sprints/sprint-07-tags-cabinets.md` | Organization |
| 8 | `/doc/sprints/sprint-08-custom-fields.md` | Organization |
| 9 | `/doc/sprints/sprint-09-search-views.md` | Organization |
| 10 | `/doc/sprints/sprint-10-workflow-engine.md` | Workflow |
| 11 | `/doc/sprints/sprint-11-rules-sources.md` | Workflow |
| 12 | `/doc/sprints/sprint-12-retention-notifications.md` | Workflow |
| 13 | `/doc/sprints/sprint-13-ml-classification.md` | Intelligence |
| 14 | `/doc/sprints/sprint-14-barcode-asn.md` | Intelligence |
| 15 | `/doc/sprints/sprint-15-llm-vector-search.md` | Intelligence |
| 16 | `/doc/sprints/sprint-16-collaboration.md` | Collaboration |
| 17 | `/doc/sprints/sprint-17-security-enterprise.md` | Collaboration |
| 18 | `/doc/sprints/sprint-18-polish-deployment.md` | Collaboration |
| 19 | `/doc/sprints/sprint-19-zone-ocr-ner-analytics.md` | Advanced Features |
| 20 | `/doc/sprints/sprint-20-relationships-portal.md` | Advanced Features |
| 21 | `/doc/sprints/sprint-21-esignatures-annotations.md` | Advanced Features |
| 22 | `/doc/sprints/sprint-22-legal-hold-dedup-physical.md` | Advanced Features |

---

## Dependencies Between Phases

```
Phase 1 (Foundation)
    |
    v
Phase 2 (Processing) ----+
    |                     |
    v                     |
Phase 3 (Organization)   |
    |                     |
    v                     |
Phase 4 (Workflow) <------+
    |
    v
Phase 5 (Intelligence)
    |
    v
Phase 6 (Collaboration & Polish)
    |
    v
Phase 7 (Advanced Features)
```

**Critical Path**: Phase 1 -> Phase 2 -> Phase 3 -> Phase 4 -> Phase 5 -> Phase 6 -> Phase 7

**Parallel Opportunities**:
- Some Phase 3 work (tags, cabinets) can start during Phase 2
- Phase 5 (ML) and Phase 4 (Workflows) are partially independent
- Phase 6 collaboration features are independent of Phase 5 AI features
- Phase 7 sprints 19-22 are largely independent of each other and can be parallelized

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|-----------|
| OCRmyPDF integration complexity | High | Start with PDF-only, add formats incrementally |
| Elasticsearch operational overhead | Medium | Provide Whoosh fallback for simple deployments |
| ML model accuracy | Medium | Start with rule-based matching, add ML incrementally |
| Frontend complexity (Angular) | Medium | Use component library (ng-bootstrap), follow Paperless-ngx patterns |
| LDAP/OIDC configuration | Low | Document common configurations, provide examples |
| Storage encryption performance | Medium | Make encryption optional, benchmark early |
| Plugin system design | High | Design interface in Sprint 4, iterate based on built-in plugins |
| E-Signature legal compliance | High | Research RFC 3161 requirements early, consider third-party TSA service |
| Zone OCR accuracy | Medium | Start with high-confidence fields only, build human review queue |
| NER extraction quality | Medium | Use spaCy with fine-tuned models, allow user corrections |
| Content-addressable migration | Medium | Run migration as background task, support rollback |

---

## Success Criteria

### Phase 1 Complete When:
- Users can register, login, create API tokens
- Documents can be created/read/updated/deleted via API
- Permissions prevent unauthorized access
- Docker Compose starts all services
- Angular app loads with login page

### Phase 2 Complete When:
- Documents can be uploaded via web UI and API
- OCR extracts text from PDFs and images
- Multiple file formats are supported
- Thumbnails are generated
- Document versions can be managed

### Phase 3 Complete When:
- Documents can be tagged, filed in cabinets, classified by type
- Custom fields can be added to documents
- Full-text search returns relevant results with highlighting
- Saved views can be created and displayed on dashboard

### Phase 4 Complete When:
- Workflow state machines can be defined and executed
- Trigger-action rules automate document processing
- Email and watch folder sources ingest documents
- Retention policies automatically clean up documents
- Notifications alert users of important events

### Phase 5 Complete When:
- ML classifier auto-suggests tags, correspondent, type
- Barcodes are detected and used for splitting/ASN
- LLM can answer questions about document content
- Semantic search finds similar documents

### Phase 6 Complete When:
- Users can share documents via links
- Comments and check-in/check-out work
- Storage encryption is available
- Production deployment is documented
- UI is polished with dark mode and multi-language support

### Phase 7 Complete When:
- Zone OCR extracts structured fields from fixed-format forms
- NER entities are indexed and browsable as search facets
- Search analytics dashboard shows query telemetry and zero-result queries
- Typed document relationships can be created and visualized as a graph
- External parties can upload documents via contributor portal
- E-Signatures can be requested and completed by external signers
- Visual annotations can be placed on document pages
- Legal holds freeze documents and track custodian acknowledgements
- Content-addressable storage deduplicates identical files
- Physical records can be tracked with charge-out register

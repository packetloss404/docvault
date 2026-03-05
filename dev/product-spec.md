# Product Specification: DocVault
## The Ultimate Open-Source Document Management System

### Version: 1.0 Draft
### Last Updated: 2026-03-01

---

## 1. Vision & Mission

### Vision
Create the definitive open-source document management system that combines enterprise-grade features with consumer-friendly usability, making professional document management accessible to individuals, small teams, and large organizations alike.

### Mission
Consolidate the best features from Lodestone (non-destructive processing, cloud-native architecture), Mayan EDMS (workflow engine, enterprise security, comprehensive ACLs), and Paperless-ngx (ML classification, modern UX, barcode intelligence) into a single, cohesive, production-ready system.

### Core Principles
1. **Best-of-breed features** - Take the proven best from each system
2. **Modern architecture** - Modular monolith with clean domain boundaries
3. **Progressive complexity** - Simple for personal use, powerful for enterprise
4. **Non-destructive by default** - Original documents are sacred
5. **AI-first** - ML classification and LLM integration as core capabilities
6. **Security-first** - Encryption, ACLs, audit trails from day one
7. **Developer-friendly** - Plugin system, comprehensive API, good documentation

---

## 2. System Architecture

### High-Level Architecture
```
                    +-----------------------+
                    |   Angular SPA (UI)    |
                    |   - Dashboard         |
                    |   - Document List     |
                    |   - Workflow Designer |
                    |   - Admin Panel      |
                    +-----------+-----------+
                                |
                    REST API + WebSocket
                                |
+---------------------------+---+---+---------------------------+
|                     Django Backend                             |
|                                                               |
|  +------------+ +------------+ +------------+ +------------+ |
|  | Documents  | | Workflows  | | Search     | | Security   | |
|  | Module     | | Module     | | Module     | | Module     | |
|  +------------+ +------------+ +------------+ +------------+ |
|  +------------+ +------------+ +------------+ +------------+ |
|  | Processing | | Storage    | | ML/AI      | | Sources    | |
|  | Module     | | Module     | | Module     | | Module     | |
|  +------------+ +------------+ +------------+ +------------+ |
|                                                               |
+---------------------------+---+-------------------------------+
                            |   |
              +-------------+   +-------------+
              |                               |
    +---------+---------+          +----------+---------+
    | Celery Workers    |          | Data Stores        |
    | - OCR Processing  |          | - PostgreSQL       |
    | - ML Training     |          | - Elasticsearch    |
    | - Email Fetching  |          | - Redis            |
    | - Index Updates   |          | - S3/MinIO Storage |
    | - Workflow Exec   |          | - FAISS Vector DB  |
    +-------------------+          +--------------------+
```

### Domain Modules

#### 2.1 Documents Module
**Responsibility**: Core document lifecycle management

**Models**:
- `Document` - Core entity with UUID, title, content, metadata
- `DocumentType` - Schema definition with retention policies, workflow assignments
- `DocumentFile` - Physical file artifacts (multiple per document)
- `DocumentVersion` - Version tracking with active version reference
- `DocumentPage` - Page-level content and metadata
- `Correspondent` - Document source/sender entity
- `StoragePath` - File system organization templates

**Features**:
- Non-destructive import (configurable per document type)
- Multi-file document support
- Full version history with diff capability
- Soft delete with trash and scheduled cleanup
- Archive Serial Number (ASN) support
- Duplicate detection via checksum (MD5 + SHA-256)
- Page count tracking
- Original filename preservation

#### 2.2 Organization Module
**Responsibility**: Document classification and organization

**Models**:
- `Tag` - Hierarchical tags (MPTT, 5-level max, color-coded)
- `Cabinet` - Hierarchical folders (MPTT, unlimited nesting)
- `CustomField` - Extensible metadata (12 data types)
- `CustomFieldInstance` - Per-document custom field values
- `MetadataType` - Structured metadata with validators/parsers
- `SmartFolder` - Dynamic folders based on saved search criteria
- `DocumentRelationship` - Typed links between documents

**Document Relationships** (Knowledge Graph):
- DocumentRelationship model: source_doc (FK), target_doc (FK), relationship_type, bidirectional (bool), created_by, created_at
- Built-in relationship types: supersedes, is-superseded-by, references, is-referenced-by, is-attachment-of, responds-to, contradicts, relates-to
- Custom relationship types (user-definable via RelationshipType model)
- Relationship panel on document detail page
- Graph visualization (network view of related documents)
- Supersession chain: explicit "this replaces that" with automatic obsolescence marking
- API: GET/POST `/api/v1/documents/{id}/relationships/`, DELETE `/api/v1/documents/{id}/relationships/{rid}/`

**Custom Field Types**:
1. STRING - Short text (max 256 chars)
2. LONGTEXT - Extended text (unlimited)
3. URL - Validated URLs
4. DATE - Date picker
5. DATETIME - Date + time picker
6. BOOLEAN - Toggle switch
7. INTEGER - Whole numbers
8. FLOAT - Decimal numbers
9. MONETARY - Currency with decimal support
10. DOCUMENTLINK - Links to other documents
11. SELECT - Dropdown with defined options
12. MULTISELECT - Multiple selection from options

**Matching Algorithms** (for auto-assignment):
- NONE, ANY, ALL, LITERAL, REGEX, FUZZY, AUTO (ML-based)

#### 2.3 Processing Module
**Responsibility**: Document ingestion, OCR, and content extraction

**Plugin Architecture**:
```python
class ProcessingPlugin(ABC):
    name: str
    order: int  # Execution priority

    @abstractmethod
    def can_run(self, context: ProcessingContext) -> bool

    @abstractmethod
    def process(self, context: ProcessingContext) -> ProcessingResult

    @abstractmethod
    def cleanup(self, context: ProcessingContext) -> None
```

**Built-in Plugins** (executed in order):
1. `PreflightPlugin` - Validate MIME type, check duplicates, verify ASN
2. `BarcodePlugin` - Detect barcodes, split documents, extract ASN/tags
3. `WorkflowTriggerPlugin` - Match consumption workflows, apply overrides
4. `PreConsumeHookPlugin` - Execute user-supplied pre-processing scripts
5. `ParserPlugin` - Route to format-specific parser
6. `OCRPlugin` - Tesseract/OCRmyPDF processing
7. `TextExtractionPlugin` - Extract and normalize text
8. `LanguageDetectionPlugin` - Detect document language
9. `DateExtractionPlugin` - Extract document date from content
10. `ClassificationPlugin` - ML-based auto-classification
11. `AIPlugin` - LLM-based analysis, embedding generation
12. `IndexPlugin` - Full-text and vector index updates
13. `ThumbnailPlugin` - Preview generation
14. `PostConsumeHookPlugin` - Execute user-supplied post-processing scripts

**Parsers** (format-specific):
- `PDFParser` - PDF via OCRmyPDF (skip/redo/force OCR modes)
- `ImageParser` - Images via OCRmyPDF + ImageMagick
- `OfficeParser` - Office docs via LibreOffice/Tika conversion
- `EmailParser` - EML/MSG with attachment extraction
- `TextParser` - Plain text and HTML
- `ArchiveParser` - ZIP/RAR extraction and recursive processing

**OCR Configuration**:
- Language selection (multi-language support)
- OCR mode: skip, redo, force
- Output type: PDF/A, PDF
- Image DPI, deskew, rotation, clean level
- Max image pixel limit
- Custom OCRmyPDF arguments

**Zone OCR / Form Template Recognition**:
- Visual zone designer: draw bounding boxes on a sample form page
- Named extraction fields (invoice_number, vendor_name, total_amount, date)
- Template matching: auto-detect which template applies to incoming documents
- Structured data extraction into custom fields
- Confidence scoring per field with human review queue for low-confidence extractions
- User correction feedback loop that improves extraction accuracy over time
- ZoneOCRTemplate model: name, sample_page_image, created_by
- ZoneOCRField model: template (FK), name, field_type, bounding_box (JSON), custom_field (FK)
- ZoneOCRPlugin (order 107, after OCR, before classification)

#### 2.4 Search Module
**Responsibility**: Full-text search, semantic search, and saved views

**Dual Search Engine**:
1. **Elasticsearch** (primary keyword search)
   - Full-text search with relevance ranking
   - Faceted search (date, type, tags, correspondent, etc.)
   - Custom field indexing
   - Permission-aware filtering
   - Highlight support
   - Aggregations for dashboard statistics

2. **FAISS** (semantic/vector search)
   - Document embeddings via HuggingFace/OpenAI
   - "More like this" similarity search
   - Natural language queries via LLM
   - Complementary to keyword search

**Saved Views**:
- Display modes: TABLE, SMALL_CARDS, LARGE_CARDS
- Customizable display fields
- Sort configuration
- Filter rules (48+ rule types)
- Dashboard integration
- Per-user customization
- Sidebar visibility

**Named Entity Recognition (NER) as Search Facets**:
- Auto-extract: persons, organizations, locations, dates, monetary amounts
- Index entities as structured facets in Elasticsearch
- Faceted entity browser in search UI (click "Acme Corp" to see all related docs)
- Entity co-occurrence graph visualization (which entities appear together)
- Configurable entity types (add custom entity categories)
- NERPlugin in processing pipeline (order 115, after AI plugin)
- Entity model: document (FK), entity_type, value, confidence, start_offset, end_offset
- EntityType model: name, color, extraction_pattern (optional regex), enabled

**Search Analytics & Relevance Tuning**:
- Search analytics dashboard: top queries, zero-result queries, click-through rates
- Query telemetry: what users search for but can't find
- Synonym management UI (admin defines synonym groups without touching ES config)
- Curations: pin or hide specific results for specific queries
- Relevance boost/bury controls per field or document
- Query suggestion model trained on user behavior (not just field values)
- SearchQuery model: query_text, user (FK), results_count, clicked_document (FK), timestamp
- SearchSynonym model: terms (ArrayField), enabled
- SearchCuration model: query_text, pinned_documents (M2M), hidden_documents (M2M)

#### 2.5 Workflow Module
**Responsibility**: Document lifecycle automation

**State Machine Engine** (from Mayan):
```
WorkflowTemplate
    |
    +--- State (initial/intermediate/final, completion %)
    |       +--- StateAction (on_entry / on_exit)
    |       +--- StateEscalation (auto-transition after timeout)
    |
    +--- Transition (origin -> destination, conditional)
    |       +--- TransitionField (custom form inputs)
    |       +--- TransitionTrigger (event-driven)
    |
    +--- WorkflowInstance (per-document runtime)
            +--- LogEntry (audit trail)
```

**Trigger-Action Engine** (from Paperless-ngx):
```
WorkflowRule
    |
    +--- Trigger
    |       - Type: CONSUMPTION, ADDED, UPDATED, SCHEDULED
    |       - Filters: filename, path, content, tags, type, custom fields
    |       - Matching: any/all/literal/regex/fuzzy
    |
    +--- Action (ordered list)
            - ADD_TAG, REMOVE_TAG
            - SET_CORRESPONDENT, SET_TYPE, SET_STORAGE_PATH
            - SET_CUSTOM_FIELD
            - ASSIGN_PERMISSIONS
            - SEND_EMAIL (with placeholders)
            - WEBHOOK (POST/PUT with headers, body)
            - LAUNCH_WORKFLOW (state machine)
            - RUN_SCRIPT
```

**Retention Policies** (per document type):
- Auto-trash after X days/weeks/months
- Auto-delete from trash after Y period
- Stub pruning for incomplete uploads
- Configurable per document type

#### 2.6 Security Module
**Responsibility**: Authentication, authorization, encryption, audit

**Authentication Backends**:
- Django native (username/password)
- LDAP/Active Directory (django-auth-ldap)
- OpenID Connect (mozilla-django-oidc)
- OAuth2 (django-allauth: Google, Microsoft, GitHub, etc.)
- Two-factor OTP (TOTP/HOTP via pyotp)
- API Token authentication

**Authorization Model**:
- **Role-Based**: Roles contain permissions, assigned to groups
- **Object-Level ACLs**: Generic ACLs on any model (from Mayan)
- **Owner-Based**: Document owners have full access
- **Permission Types**: view, change, delete, share, download, sign
- **Inheritance**: Cabinet permissions cascade to children

**Encryption**:
- **At-Rest**: AES-256-CBC file encryption (PyCryptodome)
- **In-Transit**: TLS/SSL
- **Key Management**: PBKDF2 key derivation, configurable iterations
- **Per-Storage**: Encryption configurable per storage backend

**Audit Trail**:
- Every model change logged with actor, target, timestamp
- Event types defined per module
- `@audit_event` decorator for automatic logging
- CSV/JSON export for compliance
- Retention configurable
- Dashboard widget for recent activity

**E-Signature with External Signer Flow**:
- Drag-and-drop signature field placement on PDFs
- Named signer roles with ordering (sign in sequence)
- Tokenized email links for external signers (no account needed)
- Signer identity verification (email, SMS, IP logging)
- Tamper-evident certificate of completion PDF
- Audit trail: opened, viewed per-page, signed timestamps
- RFC 3161 qualified timestamps for legal compliance
- SignatureRequest model: document (FK), created_by (FK), status, completed_at
- SignatureField model: request (FK), signer (FK or email), page, x, y, width, height, order
- Signer model: name, email, role, signed_at, ip_address, verification_method

**Legal Hold with Custodian Management**:
- LegalHold model: name, matter_number, description, created_by, status (active/released)
- LegalHoldCustodian: hold (FK), user (FK), acknowledged (bool), acknowledged_at
- Place hold: freezes all documents matching criteria (custodian, date range, tags, search query)
- Held documents cannot be deleted, modified, or have retention applied
- Custodian notification email with acknowledgement tracking
- Hold release with audit trail
- Legal hold dashboard showing active holds, pending acknowledgements
- API: GET/POST `/api/v1/legal_holds/`, POST `/api/v1/legal_holds/{id}/release/`

**Additional Security**:
- Document signing (GPG/PGP)
- Check-in/check-out locking
- Usage quotas per user/group
- IP-based access control (optional)
- Session management
- Password policies

#### 2.7 Sources Module
**Responsibility**: Document ingestion from external sources

**Source Types**:
1. **Web Upload** - Drag-and-drop, multi-file, progress tracking
2. **Watch Folders** - Filesystem directory monitoring (configurable polling)
3. **Email (IMAP)** - Account configuration, rules, OAuth2 (Gmail, Outlook)
4. **Scanner (SANE)** - Direct scanner device integration
5. **S3/Cloud Storage** - Monitor S3 buckets, GCS buckets
6. **Staging Folders** - Batch upload with preview before import
7. **REST API** - Programmatic upload with metadata
8. **Compressed Archives** - ZIP/RAR extraction with recursive processing

**Source Features**:
- Per-source document type assignment
- Per-source tag assignment
- Per-source metadata mapping
- Source metadata preservation (origin tracking)
- Configurable polling intervals
- Error handling and retry logic

#### 2.8 Storage Module
**Responsibility**: File storage abstraction and management

**Storage Backends**:
- Local filesystem (default)
- S3-compatible (MinIO, AWS S3)
- Google Cloud Storage
- Azure Blob Storage
- Encrypted local storage (AES-256)

**Storage Features**:
- Non-destructive mode (originals never modified)
- Dual storage: originals + archive (searchable PDF)
- Thumbnail storage
- WORM mode support (Write-Once-Read-Multiple)
- Checksum verification (integrity checks)
- Storage path templates (Jinja2-based)
- Deduplication support

**Content-Addressable Storage / Binary Deduplication**:
- SHA-256 content-addressed blob store
- Automatic deduplication: identical files stored once, referenced by multiple documents
- Integrity verification is inherent (address = hash)
- Storage savings reporting (how much space saved by dedup)
- Configurable per storage backend (opt-in)
- ContentBlob model: sha256_hash (primary key), size, reference_count, created_at
- Migration management command to convert existing path-addressed files

#### 2.9 ML/AI Module
**Responsibility**: Machine learning classification and AI features

**ML Classification Pipeline** (from Paperless-ngx):
- Four classifiers: tags, correspondent, document type, storage path
- Feature extraction: TF-IDF with 1-2 ngrams
- Model: MLPClassifier (scikit-learn)
- Smart caching: Redis-backed LRU for stemming
- Automatic retraining on data changes
- Confidence scoring for predictions

**LLM Integration**:
- **Providers**: OpenAI, Ollama (local), Azure AI
- **Features**:
  - Document Q&A (chat with your documents)
  - AI-powered classification
  - Content summarization
  - Entity extraction
  - Smart metadata suggestions
- **Embeddings**: HuggingFace Sentence Transformers, OpenAI
- **Vector Store**: FAISS for similarity search

#### 2.10 Collaboration Module
**Responsibility**: Multi-user features

**Features**:
- Document comments/notes (per-user, timestamped)
- Share links (slug-based, expiration, optional password)
- Share bundles (multiple documents)
- Check-in/check-out (exclusive locking with expiration)
- Per-user saved views and dashboard
- Real-time updates via WebSocket
- @mentions in comments (with notifications)
- Activity feed per document

**Document Request / Contributor Portal**:
- Guest upload links: tokenized URLs where unauthenticated users upload documents
- Document request workflow: request specific documents from specific people with deadline
- Metadata form on upload: requester fills in required fields during submission
- Persistent client portal: external parties have their own login to exchange documents over time
- Branded portal page (custom logo, colors, instructions)
- Deadline reminders via email
- Submitted documents land in a review queue before entering the archive
- DocumentRequest model: title, description, created_by, assignee_email, deadline, status, token
- PortalConfig model: name, slug, logo, welcome_text, required_fields (M2M to CustomField)

**Visual Page-Level Annotations**:
- Annotation overlay layer (separate from the PDF, non-destructive)
- Annotation types: highlight, underline, strikethrough, sticky note, freehand draw, rectangle, text box, rubber stamp
- Per-page annotations with coordinates
- Annotation author tracking
- Annotation permissions (who can view/edit)
- Export annotated PDF (bake annotations into a copy)
- W3C Web Annotation standard compliance for interoperability
- Annotation model: document (FK), page (int), type, coordinates (JSON), content, author (FK), created_at

#### 2.12 Physical Records Module
**Responsibility**: Track physical document originals alongside digital records

**Models**:
- `PhysicalLocation` - building, room, cabinet, shelf, box, position
- `ChargeOut` - document (FK), user (FK), checked_out_at, expected_return, returned_at, notes

**Features**:
- Link digital record to physical storage location
- Charge-out register: track who has the physical file
- Barcode-driven physical file checkout (scan barcode, auto-checkout)
- Destruction certificate generation on retention expiry
- Physical location search and reporting
- API: GET/POST `/api/v1/physical_locations/`, POST `/api/v1/documents/{id}/charge_out/`, POST `/api/v1/documents/{id}/charge_in/`

#### 2.13 Notifications Module
**Responsibility**: User notifications and external integrations

**Channels**:
- In-app notifications (WebSocket push)
- Email notifications (SMTP, configurable templates)
- Webhooks (configurable per event type)

**Triggers**:
- Document added/modified/deleted
- Workflow state changes
- Comment added
- Share link accessed
- Processing completed/failed
- Scheduled reminders

---

## 3. API Specification

### REST API Design
- **Framework**: Django REST Framework
- **Authentication**: Token, Session, OAuth2, API Key
- **Documentation**: OpenAPI 3.0 (drf-spectacular)
- **Versioning**: URL-based (`/api/v1/`)
- **Pagination**: Cursor-based (default 25, max 100)
- **Filtering**: django-filter with custom backends
- **Rate Limiting**: Configurable per user type

### Key Endpoints
```
# Documents
GET    /api/v1/documents/                    # List (with filters)
POST   /api/v1/documents/                    # Create
GET    /api/v1/documents/{id}/               # Retrieve
PATCH  /api/v1/documents/{id}/               # Update
DELETE /api/v1/documents/{id}/               # Soft delete
GET    /api/v1/documents/{id}/download/      # Download file
GET    /api/v1/documents/{id}/preview/       # Thumbnail
GET    /api/v1/documents/{id}/content/       # Raw text
GET    /api/v1/documents/{id}/suggestions/   # ML suggestions
GET    /api/v1/documents/{id}/metadata/      # Metadata
GET    /api/v1/documents/{id}/versions/      # Version history
POST   /api/v1/documents/{id}/checkout/      # Lock document
POST   /api/v1/documents/{id}/checkin/       # Unlock document
POST   /api/v1/documents/bulk_edit/          # Bulk operations
POST   /api/v1/documents/bulk_download/      # Batch download

# Organization
GET/POST   /api/v1/tags/
GET/POST   /api/v1/correspondents/
GET/POST   /api/v1/document_types/
GET/POST   /api/v1/storage_paths/
GET/POST   /api/v1/cabinets/
GET/POST   /api/v1/custom_fields/

# Search
GET    /api/v1/search/                       # Full-text search
GET    /api/v1/search/autocomplete/          # Typeahead
GET    /api/v1/search/similar/{id}/          # Similar documents

# Workflows
GET/POST   /api/v1/workflows/
GET/POST   /api/v1/workflow_templates/
POST       /api/v1/workflow_templates/{id}/launch/

# Sources
GET/POST   /api/v1/mail_accounts/
GET/POST   /api/v1/mail_rules/

# System
GET    /api/v1/statistics/                   # Dashboard stats
GET    /api/v1/tasks/                        # Async task status
POST   /api/v1/tasks/{id}/acknowledge/       # Mark complete
GET    /api/v1/config/                       # App configuration
GET    /api/v1/users/                        # User management
GET    /api/v1/groups/                       # Group management
GET    /api/v1/roles/                        # Role management
GET    /api/v1/audit_log/                    # Audit trail

# Sharing & Collaboration
POST   /api/v1/share_links/                 # Create share link
GET    /api/v1/share/{slug}/                 # Public access
GET/POST /api/v1/document_requests/          # Document request management
GET    /api/v1/portal/{slug}/                # Contributor portal (public)
POST   /api/v1/portal/{slug}/upload/         # Guest upload (public)

# Document Relationships
GET/POST   /api/v1/documents/{id}/relationships/   # Typed links
DELETE     /api/v1/documents/{id}/relationships/{rid}/

# Annotations
GET/POST   /api/v1/documents/{id}/annotations/     # Page-level annotations
PATCH/DEL  /api/v1/documents/{id}/annotations/{aid}/
POST       /api/v1/documents/{id}/annotations/export/  # Export annotated PDF

# E-Signatures
POST   /api/v1/documents/{id}/signature_request/    # Create signature request
GET    /api/v1/signature_requests/                   # List my requests
GET    /api/v1/sign/{token}/                         # External signer endpoint (public)
POST   /api/v1/sign/{token}/complete/                # Submit signature (public)

# Legal Hold
GET/POST   /api/v1/legal_holds/              # Legal hold management
POST       /api/v1/legal_holds/{id}/release/ # Release hold

# Search Analytics
GET    /api/v1/search/analytics/             # Search analytics dashboard
GET/POST /api/v1/search/synonyms/            # Synonym management
GET/POST /api/v1/search/curations/           # Search curations

# NER Entities
GET    /api/v1/entities/                     # Browse extracted entities
GET    /api/v1/entities/types/               # Entity types
GET    /api/v1/entities/graph/               # Entity co-occurrence graph

# Zone OCR
GET/POST   /api/v1/zone_ocr_templates/       # Zone OCR templates
POST       /api/v1/zone_ocr_templates/{id}/test/  # Test template on document

# Physical Records
GET/POST   /api/v1/physical_locations/        # Physical location management
POST       /api/v1/documents/{id}/charge_out/ # Check out physical file
POST       /api/v1/documents/{id}/charge_in/  # Return physical file
```

### WebSocket API
```
ws://host/ws/status/         # Task progress updates
ws://host/ws/notifications/  # Real-time notifications
ws://host/ws/documents/      # Document change events
```

---

## 4. UI/UX Specification

### Design Principles
- **Search-first**: Primary interaction is search, not browsing
- **Progressive disclosure**: Simple by default, powerful on demand
- **Responsive**: Mobile-friendly responsive design
- **Accessible**: WCAG 2.1 AA compliance
- **Themeable**: Light/dark mode, custom color schemes
- **Localized**: 30+ languages

### Key Views

#### 4.1 Dashboard
- Drag-and-drop widget layout
- Widgets: Welcome, Statistics, Recent Documents, Saved Views, Upload, Activity Feed, Workflow Queue
- Per-user customization
- Quick action buttons

#### 4.2 Document List
- Three display modes: Table, Small Cards, Large Cards
- Configurable columns (title, date, tags, correspondent, type, ASN, custom fields, etc.)
- Advanced filter builder (48+ rule types)
- Bulk selection and operations
- Sort by any column
- Pagination with configurable page size

#### 4.3 Document Detail
- Tabs: Details, Content, Preview, Notes, Permissions, Workflow, History, Versions
- PDF viewer with zoom, rotation, page navigation
- Inline metadata editing
- Tag management with autocomplete
- Version comparison
- Activity timeline

#### 4.4 Workflow Designer
- Visual state machine builder (drag-and-drop)
- State/transition/action configuration panels
- Condition editor with syntax highlighting
- Testing/simulation mode

#### 4.5 Admin Panel
- User/group/role management
- Source configuration
- Storage backend management
- System health dashboard
- Audit log viewer
- Configuration editor

#### 4.6 Global Search
- Real-time typeahead across all entities
- Saved search history
- Advanced query syntax support
- Filter integration
- Keyboard navigation (Ctrl+K shortcut)

---

## 5. Non-Functional Requirements

### Performance
- Document upload: < 2s for files under 10MB
- Search results: < 500ms for typical queries
- Page load: < 1s for all views
- OCR processing: Async, non-blocking
- Support 10,000+ documents per user
- Support 100+ concurrent users

### Scalability
- Horizontal scaling via Celery workers
- Elasticsearch cluster support
- S3-compatible storage for unlimited files
- Redis cluster for high availability
- Database read replicas (PostgreSQL)

### Reliability
- Soft deletes with configurable retention
- Checksum verification for file integrity
- Automatic retry for failed processing tasks
- Health check endpoints for monitoring
- Graceful degradation (search down != system down)

### Security
- OWASP Top 10 compliance
- SOC 2 alignment
- GDPR compliance features (data export, right to deletion)
- Regular dependency vulnerability scanning
- Content Security Policy headers
- CORS configuration

### Deployment
- Docker Compose for single-node deployment
- Kubernetes Helm chart for production
- Environment variable configuration
- Health check endpoints (/health, /ready)
- Prometheus metrics endpoint
- Structured JSON logging

---

## 6. Technology Stack Summary

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | Angular 21+ | Proven in Paperless-ngx, TypeScript, modern |
| Backend | Django 5.x | Proven in both Mayan and Paperless, rich ecosystem |
| API | DRF + drf-spectacular | Industry standard, auto-generated docs |
| Database | PostgreSQL 16+ | Production-grade, both systems recommend it |
| Search | Elasticsearch 8.x | Scales better than Whoosh, faceted search |
| Vector DB | FAISS | Proven in Paperless-ngx for semantic search |
| Task Queue | Celery 5.x + Redis | Proven in both systems |
| OCR | OCRmyPDF (Tesseract) | Better than raw Tesseract, PDF/A output |
| ML | scikit-learn | Proven classification pipeline |
| LLM | OpenAI + Ollama | Flexibility: cloud + local LLM |
| Storage | S3-compatible + Local | MinIO self-hosted, AWS S3 for cloud |
| Auth | allauth + LDAP + OTP | Consumer + enterprise coverage |
| Permissions | django-guardian + custom | Object-level + role-based |
| Real-time | Django Channels + Redis | WebSocket for live updates |
| Container | Docker + s6-overlay | Proven init system from Paperless-ngx |
| CI/CD | GitHub Actions | Standard for open-source |

# Mayan EDMS - Deep Dive Analysis

## Executive Summary

Mayan EDMS is a comprehensive, enterprise-grade Electronic Document Management System built on Django. It features the most sophisticated workflow engine, granular ACL-based permissions, and the widest range of document ingestion sources among the three systems analyzed. With 100+ Django apps, it follows a highly modular architecture pattern.

**Project Maturity:** Production-ready (v4.11+)
**License:** Open Source (Apache 2.0)
**Target Audience:** Enterprise / organizational document management

---

## 1. Technical Architecture

### Tech Stack
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Django | v5.2.11 |
| Language | Python | 3.13 |
| API | Django REST Framework | v3.16.1 |
| Task Queue | Celery | v5.6.2 |
| WSGI Server | Gunicorn + Gevent | v25.1.0 |
| Search | Elasticsearch 9.3 / Whoosh 2.7.4 | Dual support |
| OCR | Tesseract OCR | System package |
| Document Conversion | LibreOffice | System package |
| Authentication | LDAP + OIDC + OTP | Multiple backends |
| Encryption | PyCryptodome (AES-256-CBC) | v3.23.0 |
| AI/ML | OpenAI + Ollama | v1.109.1 / v0.6.1 |
| Storage | S3/GCS/Local/Encrypted | Multiple backends |

### Architecture Pattern
**Monolithic Django application** with modular app-based architecture:
```
Web Layer (Django/DRF + Gunicorn)
    |
    v
REST API Layer (DRF ViewSets with ACL filtering)
    |
    v
Business Logic Layer (Model Mixins)
    |
    v
ORM Layer (Django Models, MPTT Trees)
    |
    +---> Celery Task Queue (async processing)
    |
    v
Database (PostgreSQL/MySQL/SQLite)
Storage Backend (S3/GCS/Filesystem/Encrypted)
```

### Modular App Organization (100+ Django Apps)
**Document Core:**
- `documents` - Core models (Document, DocumentFile, DocumentVersion, DocumentType)
- `document_parsing` - Text extraction
- `document_indexing` - Search index management
- `document_states` - Workflow engine
- `document_comments` - Commenting system
- `document_signatures` - Digital signatures
- `document_exports` - Export functionality

**Processing:**
- `converter` - Format conversion (LibreOffice)
- `ocr` - Tesseract OCR with multi-language support
- `file_caching` - Preview caching
- `file_metadata` - EXIF, ClamAV, EML, MSG, PDF, AI-based metadata extraction

**Organization:**
- `metadata` - Custom metadata types with validators/parsers/lookups
- `cabinets` - MPTT-based hierarchical folders
- `tags` - Color-coded tags
- `linking` - Document linking

**Security:**
- `acls` - Generic Access Control Lists
- `permissions` - Role-based permission system
- `authentication` - Multi-backend auth (LDAP, OIDC)
- `authentication_otp` - Two-factor authentication
- `quotas` - Usage quotas

**Ingestion Sources (11+ types):**
- `source_interactive` - Web form uploads
- `source_watch_folders` - Filesystem monitoring
- `source_watch_storages` - Cloud storage monitoring
- `source_staging_folders` - Batch upload staging
- `source_emails` - Email gateway
- `source_compressed` - ZIP/RAR extraction
- `source_sane_scanners` - Scanner integration
- `source_periodic` - Scheduled imports
- `source_web_forms` - Custom web forms
- `source_stored_files` - Internal storage source
- `source_generated_files` - Dynamic generation

---

## 2. Data Model

### Document Hierarchy
```
DocumentType (schema + retention policies + workflows)
    |
    v
Document (UUID-based, globally unique)
    |
    +--- DocumentFile (multiple files per document)
    |       |
    |       +--- DocumentFilePage (page-level content)
    |
    +--- DocumentVersion (active version tracking)
            |
            +--- DocumentVersionPage (versioned pages)
                    |
                    +--- DocumentVersionPageOCRContent (OCR text)
```

### Document Model Fields
- UUID (globally unique)
- Label, Description, Language
- DocumentType (ForeignKey)
- InTrash / TrashedDateTime (soft delete)
- IsStub (incomplete upload tracking)
- VersionActive (OneToOne to active version)
- FileLatest (OneToOne to latest file)

### DocumentType Features
- Configurable filename generators
- **Retention Policies**: Auto-trash after X days/weeks/months, auto-delete after Y period
- Stub pruning (cleanup incomplete uploads)
- Workflow assignment (M2M)
- Index template assignment
- Metadata type assignment

### Metadata System
- **MetadataType**: Name, label, default value template, lookup template, validation class, parser class
- **DocumentMetadata**: Per-document metadata instances with validation
- Dynamic templates for defaults and lookup values
- Per-document-type metadata association

---

## 3. Workflow Engine (Key Differentiator)

### State Machine Architecture
```
WorkflowTemplate
    |
    +--- WorkflowState (initial, intermediate, final)
    |       |
    |       +--- WorkflowStateAction (on_entry / on_exit)
    |       +--- WorkflowStateEscalation (auto-transition after timeout)
    |
    +--- WorkflowTransition (origin -> destination, conditional)
    |       |
    |       +--- WorkflowTransitionField (custom UI form fields)
    |       +--- WorkflowTransitionTriggerEvent (event-based triggers)
    |
    +--- WorkflowInstance (per-document runtime)
            |
            +--- WorkflowInstanceLogEntry (audit trail)
```

### Workflow Features
- **State Properties**: Initial/final flags, completion percentage (0-100)
- **Conditional Transitions**: Python expressions evaluated against workflow context
- **Event-Driven Triggers**: Any system event can trigger transitions
- **State Actions**: Execute on entry/exit - alphabetical ordering
- **Escalation**: Auto-transition after configurable timeout with conditions
- **Transition Fields**: Custom form fields for user input during transitions
- **Context Storage**: JSON-based workflow instance data

### Available Workflow Actions
- `DocumentPropertiesEditAction` - Modify document label/description
- `DocumentWorkflowLaunchAction` - Trigger other workflows
- `DocumentMetadataSetAction` - Set/update metadata
- `DocumentTagAddAction` - Apply tags
- `DocumentCabinetAddAction` - Add to cabinets
- `WebhookAction` - HTTP POST to external systems
- `EmailAction` - Send email notifications
- `JavaScriptAction` - Execute JavaScript code
- `HTTPRequestAction` - Flexible HTTP calls with response caching
- `TransitionFieldAction` - Populate form fields

---

## 4. Security Model

### Authentication (4 backends)
1. Django native (username/password)
2. LDAP (django-auth-ldap, nested groups)
3. OpenID Connect (mozilla-django-oidc)
4. Two-factor OTP (pyotp, TOTP/HOTP)

### Access Control Lists (Generic ACLs)
- **Model**: `AccessControlList` with GenericForeignKey
- Can protect ANY Django model (documents, cabinets, indexes, etc.)
- Maps Role + Permission + Object
- Supports queryset filtering by permissions

### Role-Based Permissions
- **Role**: Collection of permissions assigned to groups
- **StoredPermission**: Namespaced permissions (e.g., `documents.view`)
- System-wide permissions via roles
- Object-level permissions via ACLs

### Encryption
- **AES-256-CBC** file storage encryption via PyCryptodome
- PBKDF2 key derivation with configurable iterations
- Random IV per file
- GPG/PGP support for document signing
- QR code generation for tokens

### Check-in/Check-out
- Exclusive document locking (one user at a time)
- Expiration-based auto-release
- Optional blocking of new file uploads during checkout
- Forced check-in by administrators

---

## 5. Processing Pipeline

### File Upload Sequence (Celery Chord Pattern)
```
task_document_file_upload
    |
    v
task_document_file_create --> task_document_file_size_update
    --> task_document_file_checksum_update (SHA-256)
    --> task_document_file_mimetype_update
    --> task_document_file_page_count_update
    --> task_document_file_version_create
    --> OCR/Parsing tasks
```

### Text Extraction
- **PopplerParser**: pdftotext for PDFs (page-by-page)
- **OfficePopplerParser**: Convert Office to PDF first, then extract
- Plugin registry pattern for extensibility

### OCR Pipeline
- Celery Chord for parallel page processing
- Tesseract integration with multi-language support
- Transformation pipeline (rotation, scaling) before OCR
- Lock-based concurrent processing guard

---

## 6. Event System & Audit Trail

### Event Architecture
- **EventType**: Classification of what happened
- **Event Metadata**: Actor, target, action_object, timestamp, extra_data
- **`@method_event` decorator**: Automatic event recording on model operations
- **Event Subscriptions**: Users subscribe to specific event types
- **CSV Export**: `ActionExporter` for compliance reporting
- **Notification Channels**: Email, in-app, webhooks

---

## 7. API Design

### REST API Features
- DRF ViewSets with ACL-based filtering (`MayanObjectPermissionsFilter`)
- Hyperlinked serializers (HATEOAS-style)
- Dynamic field inclusion/exclusion
- Rate limiting: 5/sec anonymous, 10/sec authenticated
- OpenAPI/Swagger documentation (drf-yasg)
- Token + Session + Basic authentication

---

## 8. Strengths (Features to Adopt)

1. **Workflow engine** - Most sophisticated state machine implementation
2. **Granular ACLs** - Generic, object-level permissions on any model
3. **11+ ingestion sources** - Most comprehensive source system
4. **Document retention policies** - Auto-trash/delete with configurable timelines
5. **Check-in/check-out** - Proper document locking for collaboration
6. **AES-256 storage encryption** - Enterprise-grade at-rest encryption
7. **LDAP + OIDC + OTP** - Enterprise authentication
8. **Metadata system** - Custom validators, parsers, lookups, templates
9. **MPTT cabinets** - Efficient hierarchical folder system
10. **Event/audit system** - Comprehensive audit trail with decorators
11. **Document signatures** - GPG/PGP signing support
12. **Usage quotas** - Per-user/org resource limits
13. **Multi-language OCR** - Per-document language configuration
14. **Plugin/backend pattern** - Extensible via registries

---

## 9. Weaknesses / Gaps

1. **Server-side rendered UI** - Django templates, not a modern SPA
2. **No ML-based classification** - No auto-tagging or smart matching
3. **No barcode detection** - No ASN or document splitting
4. **No custom fields** - Metadata types are limited compared to Paperless-ngx
5. **Complex configuration** - 100+ apps can be overwhelming
6. **Higher resource requirements** - LibreOffice, Tesseract, Elasticsearch all needed
7. **No document sharing links** - No guest access URLs
8. **No FUSE vector search** - No semantic/AI-powered search
9. **No dark mode** - Limited UI theming
10. **Steeper learning curve** - Enterprise complexity

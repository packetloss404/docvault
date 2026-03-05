# Paperless-ngx - Deep Dive Analysis

## Executive Summary

Paperless-ngx is the most popular and actively maintained open-source document management system. It combines a Django backend with a modern Angular SPA frontend, featuring ML-powered auto-classification, barcode detection, custom fields, and an excellent user experience. It strikes the best balance between features, usability, and maintainability.

**Project Maturity:** Production-ready, very actively maintained
**License:** GNU GPL v3
**Target Audience:** Home users to small/medium organizations

---

## 1. Technical Architecture

### Tech Stack
| Component | Technology | Version |
|-----------|-----------|---------|
| Backend | Django | v5.2.10 |
| Frontend | Angular | v21.2.0 |
| API | Django REST Framework | v3.16 |
| Task Queue | Celery | v5.6.2 |
| Message Broker | Redis | hiredis optimized |
| WebSocket | Django Channels | v4.2 |
| Full-Text Search | Whoosh | v2.7.5+ |
| Vector Search | FAISS | Facebook AI |
| OCR | Tesseract via OCRmyPDF | v16.13.0 |
| ML Classification | scikit-learn | v1.7.0 |
| LLM Integration | OpenAI + Ollama | Via llama-index |
| Permissions | django-guardian | v3.3.0 |
| SSO | django-allauth | v65.14.0 |
| Web Server | Granian (ASGI) | v2.7.0 |
| Init System | s6-overlay | v3.2.1.0 |

### Architecture Pattern
**Monolithic Django application** with Angular SPA frontend:
```
Angular SPA Frontend (src-ui/)
    |  REST API + WebSocket
    v
Django Backend (src/)
    |
    +--- DRF ViewSets + Serializers (Permission-aware)
    |
    +--- Core Services & Business Logic
    |       - Consumer Pipeline (plugin-based)
    |       - ML Classifier (scikit-learn)
    |       - Whoosh Full-Text Index
    |       - FAISS Vector Store
    |
    +--- Celery Task Queue (Redis broker)
    |       - consume_file, train_classifier
    |       - index_optimize, process_mail
    |
    v
PostgreSQL/SQLite + Media Storage + Index Dir + AI Models
```

### Django Apps
- `documents` - Core document management (1750-line models.py, 4019-line views.py)
- `paperless` - Settings, configuration, main app
- `paperless_mail` - Email account/rule models + IMAP fetch
- `paperless_ai` - LLM integration, embeddings, AI classification
- `paperless_tesseract` - OCR engine wrapper
- `paperless_text` - Text extraction
- `paperless_tika` - Tika document parsing
- `paperless_remote` - Remote workflow/action execution

---

## 2. Data Model

### Core Models

**Document** (extends SoftDeleteModel, ModelWithOwner):
- `title` (CharField, max 128)
- `content` (TextField - full OCR text)
- `content_length` (GeneratedField - auto-computed)
- `correspondent` (ForeignKey)
- `document_type` (ForeignKey)
- `storage_path` (ForeignKey)
- `tags` (ManyToManyField)
- `filename` / `archive_filename` (FilePathField, unique)
- `original_filename` (CharField)
- `checksum` / `archive_checksum` (MD5 hashes)
- `mime_type` (CharField)
- `page_count` (PositiveIntegerField)
- `archive_serial_number` (PositiveIntegerField, unique) - ASN
- `created` / `modified` / `added` (DateTime fields)
- `owner` (ForeignKey to User)
- `root_document` (self-ForeignKey for versioning)
- `version_label` (CharField)

**MatchingModel** (base for Correspondent, Tag, DocumentType, StoragePath):
- Six matching algorithms: NONE, ANY, ALL, LITERAL, REGEX, FUZZY, AUTO (ML)
- `name`, `match` pattern, `matching_algorithm`, `is_insensitive`

**Tag** (extends MatchingModel + TreeNodeModel):
- Hierarchical with max 5 nesting levels
- Color support for UI
- Inbox tag designation

**CustomField** (10 data types):
- STRING, URL, DATE, BOOLEAN, INTEGER, FLOAT, MONETARY, DOCUMENTLINK, SELECT, LONGTEXT

**Workflow System**:
- `WorkflowTrigger`: 4 types (CONSUMPTION, DOCUMENT_ADDED, DOCUMENT_UPDATED, SCHEDULED)
- `WorkflowAction`: Tag assignment, email, webhook, permissions
- `Workflow`: Links triggers to actions

**ShareLink / ShareLinkBundle**:
- Slug-based URLs with expiration
- File version selection (original/archive)
- Bundle support for multiple documents

---

## 3. ML Classification Pipeline (Key Differentiator)

### Architecture
```python
class DocumentClassifier:
    # Four separate classifiers:
    tags_classifier        # Multi-label (MultiLabelBinarizer + MLPClassifier)
    correspondent_classifier   # Single-label
    document_type_classifier   # Single-label
    storage_path_classifier    # Single-label

    # Feature extraction:
    data_vectorizer = CountVectorizer(ngram_range=(1,2), min_df=0.01)

    # Smart caching:
    _stem_cache = StoredLRUCache(capacity=10000)  # Redis-backed
```

### Training Logic
- Only trains on documents with `MATCH_AUTO` algorithm
- Tracks hash of AUTO-matched document IDs to avoid unnecessary retraining
- Content preprocessing: regex tokenization, case normalization, Snowball stemming, stop word filtering
- Large document handling: crops to 1.2M chars (800k start + 200k end)
- 50-minute cache invalidation

### Matching Algorithms (6 types)
1. **MATCH_NONE**: Never match
2. **MATCH_ANY**: Any word present
3. **MATCH_ALL**: All words present
4. **MATCH_LITERAL**: Exact string match
5. **MATCH_REGEX**: Regular expression
6. **MATCH_FUZZY**: Approximate matching
7. **MATCH_AUTO**: ML-based prediction (the differentiator)

---

## 4. Document Processing Pipeline (Plugin-Based)

### ConsumeTaskPlugin Architecture
```python
class ConsumeTaskPlugin(ABC):
    able_to_run: bool      # Check if plugin should run
    setup() -> None        # Pre-processing
    run() -> str | None    # Main logic
    cleanup() -> None      # Post-processing
    _send_progress()       # Report progress
```

### Processing Flow
```
Document Upload (Web/API/Email/Folder)
    |
    v
ConsumerPreflightPlugin (validate MIME, check duplicates)
    |
    v
WorkflowTriggerPlugin (match filters, apply rules)
    |
    v
Pre-consume Scripts (user-supplied shell scripts)
    |
    v
Format Detection & Parser Selection
    - PdfParser (OCRmyPDF)
    - ImageParser (OCRmyPDF + convert)
    - OfficeParser (LibreOffice/Tika)
    - MailParser (email attachments)
    - TextParser (plain text/HTML)
    - ArchiveParser (ZIP extraction)
    |
    v
OCR Processing (Tesseract via OCRmyPDF)
    - Language detection, deskew, rotation
    - Page-by-page processing
    |
    v
Post-parse Processing
    - Text normalization
    - Language detection (langdetect)
    - Date extraction (regex + dateparser)
    - Barcode detection (zxing-cpp)
    |
    v
File Storage (originals + archive PDFs + thumbnails)
    |
    v
ML Classification (auto-tag, auto-correspondent, auto-type)
    |
    v
AI Features (optional: LLM classification, embeddings, vector index)
    |
    v
Whoosh Full-Text Indexing
    |
    v
Post-consume Scripts
```

---

## 5. Search Capabilities

### Whoosh Full-Text Search
- 20+ indexed fields (title, content, correspondent, tags, ASN, dates, notes, custom fields, owner, page count)
- MultiField parser with date plugins
- TF-IDF scoring
- Async writer for non-blocking updates
- Permission-aware filtering

### FAISS Vector Search (AI-powered)
- Facebook AI Similarity Search for semantic queries
- Document embeddings via HuggingFace/OpenAI
- llama-index integration for document Q&A
- Separate from keyword search - complementary

### Saved Views
- Three display modes: TABLE, SMALL_CARDS, LARGE_CARDS
- 48+ filter rule types
- Dashboard integration (show_on_dashboard, show_in_sidebar)
- Per-user customization

---

## 6. Barcode Detection & ASN System

### Capabilities
- **zxing-cpp**: Code128, QR, UPC, and more
- **Separator barcodes**: Split multi-document scans
- **ASN barcodes**: Extract archive serial numbers with prefix matching
- **Tag barcodes**: Extract tags via regex mapping with auto-creation
- **Configuration**: DPI, upscaling, max pages, retention control

---

## 7. UI/UX (Angular SPA)

### Dashboard
- Drag-droppable widget layout
- Welcome, statistics, file upload, saved view widgets
- Customizable per-user

### Document List
- Three display modes (table, small cards, large cards)
- 11+ displayable fields with custom field support
- Sortable columns, pagination, bulk selection/editing
- Complex filter editor

### Document Detail
- 7 tabs: Details, Content, Metadata, Preview, Notes, Permissions, History
- PDF/image preview with zoom, rotation, page navigation
- Inline metadata editing
- Version history

### Global Search
- Real-time typeahead across all entity types
- Quick creation from search
- Keyboard navigation

### Multi-language & Theming
- 30+ languages via Crowdin
- Dark mode support
- Multiple themes

---

## 8. Permissions & Multi-User

### django-guardian Object-Level Permissions
- Model-level: add, change, delete, view
- Object-level: per-document, per-tag, etc.
- Owner always has full access
- Group-based permission assignment
- Cascading permissions (change implies view)

### Multi-User Features
- Individual saved views per user
- User-specific document filtering
- Per-user UI settings (theme, language, dashboard)
- Notes per user
- Share links with expiration and optional password

---

## 9. Email Integration

### IMAP Support
- Mail account configuration (server, port, SSL/STARTTLS)
- Mail rules with filtering (from, subject, folder)
- Attachment extraction
- OAuth2 support (Gmail, Outlook)
- Scheduled fetching (configurable cron)

---

## 10. Workflow Automation

### Trigger Types
1. CONSUMPTION_STARTED
2. DOCUMENT_ADDED
3. DOCUMENT_UPDATED
4. SCHEDULED (recurring with interval)

### Matching Options
- Source filtering (consume folder, API, email, web UI)
- File path/filename glob patterns
- Content matching (any word, all words, literal, regex, fuzzy)
- Tag/correspondent/document type/storage path filtering
- Custom field value matching

### Action Types
- Tag assignment/removal
- Correspondent/document type/storage path assignment
- Custom field value setting
- Permission assignment
- Email notifications (with placeholders)
- Webhook (POST/PUT with headers, JSON body)

---

## 11. Strengths (Features to Adopt)

1. **ML-powered auto-classification** - Unique scikit-learn pipeline for auto-tagging
2. **Barcode intelligence** - ASN system, document splitting, tag extraction
3. **Modern Angular SPA** - Best UI/UX of the three systems
4. **Custom fields** - 10 data types including document links and selects
5. **Plugin architecture** - ConsumeTaskPlugin for extensible processing
6. **FAISS vector search** - Semantic search alongside keyword search
7. **LLM integration** - OpenAI/Ollama for document Q&A and classification
8. **Share links** - Guest access with expiration and passwords
9. **Hierarchical tags** - 5-level TreeNode with colors
10. **Document versioning** - Root document + versions
11. **Soft deletes** - Trash functionality with scheduled cleanup
12. **Comprehensive API** - Full DRF with OpenAPI docs
13. **WebSocket real-time updates** - Django Channels
14. **Pre/post-consume scripts** - Hook-based extensibility
15. **Multi-database support** - PostgreSQL, MySQL, SQLite

---

## 12. Weaknesses / Gaps

1. **No granular ACLs** - Owner-based, not role+object ACLs like Mayan
2. **No check-in/check-out** - No document locking for collaboration
3. **No storage encryption** - No at-rest encryption
4. **No LDAP authentication** - Only OAuth/allauth (no enterprise LDAP)
5. **Simple workflow engine** - Trigger/action only, no state machines
6. **No document signing** - No GPG/PGP support
7. **No retention policies** - No auto-trash/delete by document type
8. **No usage quotas** - No per-user resource limits
9. **No scanner integration** - No SANE support
10. **Whoosh limitations** - Pure-Python search less performant than Elasticsearch at scale

# DocVault - Technical Architecture Document

### Version: 1.0 Draft
### Last Updated: 2026-03-01

---

## 1. Architecture Overview

### Pattern: Modular Monolith with Plugin Architecture

DocVault uses a **modular monolith** pattern - a single deployable Django application with clear domain boundaries enforced by Django apps. This avoids the operational complexity of microservices (Lodestone's 9+ containers) while maintaining the modularity of Mayan's 100+ apps approach, but with fewer, more cohesive modules.

### Why Modular Monolith?
| Approach | Pros | Cons | Used By |
|----------|------|------|---------|
| Microservices | Independent scaling, tech diversity | Complex orchestration, debugging | Lodestone |
| Django mega-monolith | Simple deployment | Tight coupling, hard to test | Mayan (100+ apps) |
| **Modular monolith** | Simple deployment, clear boundaries | Must enforce boundaries | **DocVault** |

### System Context Diagram
```
+------------------+     +------------------+     +------------------+
|   Web Browser    |     |   Mobile App     |     |  External APIs   |
|   (Angular SPA)  |     |   (Future)       |     |  (Webhooks)      |
+--------+---------+     +--------+---------+     +--------+---------+
         |                         |                        |
         +------------+------------+------------------------+
                      |
              HTTPS / WSS
                      |
         +------------+------------+
         |    Reverse Proxy        |
         |    (Nginx/Caddy)        |
         +------------+------------+
                      |
    +-----------------+------------------+
    |         DocVault Application       |
    |                                    |
    |  +----------+  +----------+       |
    |  | Django   |  | Celery   |       |
    |  | (ASGI)   |  | Workers  |       |
    |  | Granian  |  | (N procs)|       |
    |  +----+-----+  +----+-----+       |
    |       |              |            |
    +-------+--------------+------------+
            |              |
    +-------+--------------+------------+
    |                                    |
    |  +-----------+  +----------+      |
    |  | PostgreSQL|  | Redis    |      |
    |  | (Primary) |  | (Cache/  |      |
    |  |           |  |  Broker) |      |
    |  +-----------+  +----------+      |
    |                                    |
    |  +-----------+  +----------+      |
    |  | Elastic-  |  | FAISS    |      |
    |  | search    |  | (Vector) |      |
    |  +-----------+  +----------+      |
    |                                    |
    |  +-----------+                    |
    |  | S3/MinIO  |                    |
    |  | (Storage) |                    |
    |  +-----------+                    |
    +------------------------------------+
```

---

## 2. Django App Structure

### Module Layout
```
docvault/
├── manage.py
├── docvault/                      # Project config
│   ├── settings/
│   │   ├── __init__.py            # Main settings (env-based)
│   │   ├── base.py                # Base configuration
│   │   ├── production.py          # Production overrides
│   │   └── development.py         # Dev overrides
│   ├── celery.py                  # Celery app
│   ├── asgi.py                    # ASGI + Channels
│   ├── wsgi.py                    # WSGI fallback
│   └── urls.py                    # Root URL conf
│
├── core/                          # Core utilities
│   ├── models.py                  # Base models (SoftDelete, Auditable, Owned)
│   ├── permissions.py             # Permission framework
│   ├── serializers.py             # Base serializers
│   ├── views.py                   # Base viewsets
│   ├── plugins.py                 # Plugin registry
│   ├── events.py                  # Event system
│   ├── encryption.py              # AES encryption utilities
│   └── middleware.py              # Custom middleware
│
├── documents/                     # Document management
│   ├── models/
│   │   ├── document.py            # Document, DocumentFile, DocumentVersion
│   │   ├── document_type.py       # DocumentType with retention
│   │   └── page.py                # DocumentPage
│   ├── views.py                   # DRF ViewSets
│   ├── serializers.py             # Serializers
│   ├── filters.py                 # FilterSets
│   ├── consumers.py               # WebSocket consumers
│   └── tasks.py                   # Celery tasks
│
├── organization/                  # Classification & organization
│   ├── models/
│   │   ├── tag.py                 # Hierarchical tags (MPTT)
│   │   ├── correspondent.py       # Correspondents
│   │   ├── cabinet.py             # Hierarchical cabinets (MPTT)
│   │   ├── custom_field.py        # Custom fields (12 types)
│   │   └── metadata.py            # Metadata types
│   ├── matching.py                # Matching algorithms
│   └── views.py
│
├── processing/                    # Document processing pipeline
│   ├── plugins/
│   │   ├── base.py                # ProcessingPlugin ABC
│   │   ├── preflight.py           # Validation plugin
│   │   ├── barcode.py             # Barcode detection
│   │   ├── parser.py              # Format routing
│   │   ├── ocr.py                 # OCR processing
│   │   ├── text_extraction.py     # Text extraction
│   │   ├── language.py            # Language detection
│   │   ├── date_extraction.py     # Date parsing
│   │   ├── hooks.py               # Pre/post consume
│   │   └── thumbnail.py           # Preview generation
│   ├── parsers/
│   │   ├── base.py                # Parser ABC
│   │   ├── pdf.py                 # PDF parser (OCRmyPDF)
│   │   ├── image.py               # Image parser
│   │   ├── office.py              # Office parser (Tika/LibreOffice)
│   │   ├── email.py               # Email parser
│   │   ├── text.py                # Text parser
│   │   └── archive.py             # Archive parser
│   ├── consumer.py                # Main consumer orchestrator
│   └── tasks.py                   # Celery tasks
│
├── search/                        # Search & indexing
│   ├── backends/
│   │   ├── elasticsearch.py       # Elasticsearch backend
│   │   └── faiss_backend.py       # FAISS vector search
│   ├── index.py                   # Index management
│   ├── views.py                   # Search API
│   └── tasks.py                   # Index update tasks
│
├── workflows/                     # Workflow engine
│   ├── models/
│   │   ├── template.py            # WorkflowTemplate
│   │   ├── state.py               # WorkflowState, StateAction, StateEscalation
│   │   ├── transition.py          # Transitions, fields, triggers
│   │   ├── instance.py            # WorkflowInstance, LogEntry
│   │   └── rules.py               # Trigger-Action rules
│   ├── engine.py                  # State machine execution
│   ├── actions.py                 # Built-in action implementations
│   ├── conditions.py              # Condition evaluator
│   └── tasks.py                   # Async workflow execution
│
├── security/                      # Authentication & authorization
│   ├── models/
│   │   ├── role.py                # Roles and permissions
│   │   ├── acl.py                 # Access Control Lists
│   │   └── quota.py               # Usage quotas
│   ├── authentication.py          # Auth backends
│   ├── permissions.py             # Permission checking
│   ├── encryption.py              # File encryption
│   ├── signing.py                 # Document signing (GPG)
│   ├── audit.py                   # Audit logging
│   └── views.py                   # Auth API endpoints
│
├── sources/                       # Document ingestion
│   ├── backends/
│   │   ├── base.py                # Source ABC
│   │   ├── web_upload.py          # Web form upload
│   │   ├── watch_folder.py        # Filesystem monitoring
│   │   ├── email_source.py        # IMAP email
│   │   ├── scanner.py             # SANE scanner
│   │   ├── s3_source.py           # S3 bucket monitoring
│   │   ├── staging.py             # Staging folders
│   │   └── compressed.py          # Archive extraction
│   ├── models.py                  # Source configuration
│   └── tasks.py                   # Polling tasks
│
├── storage/                       # File storage abstraction
│   ├── backends/
│   │   ├── local.py               # Local filesystem
│   │   ├── s3.py                  # S3-compatible
│   │   ├── gcs.py                 # Google Cloud Storage
│   │   ├── encrypted.py           # AES-256 encrypted
│   │   └── worm.py                # Write-Once-Read-Multiple
│   ├── models.py                  # Storage path templates
│   └── utils.py                   # Checksum, dedup
│
├── ml/                            # Machine learning
│   ├── classifier.py              # Document classifier
│   ├── embeddings.py              # Embedding generation
│   ├── llm_client.py              # LLM abstraction (OpenAI/Ollama)
│   ├── chat.py                    # Document Q&A
│   └── tasks.py                   # Training tasks
│
├── collaboration/                 # Multi-user features
│   ├── models/
│   │   ├── comment.py             # Document comments
│   │   ├── share.py               # Share links
│   │   └── checkout.py            # Check-in/check-out
│   ├── views.py
│   └── consumers.py               # WebSocket consumers
│
├── notifications/                 # Notification system
│   ├── models.py                  # Notification preferences
│   ├── channels/
│   │   ├── email.py               # Email notifications
│   │   ├── websocket.py           # Real-time push
│   │   └── webhook.py             # Webhook delivery
│   └── tasks.py
│
└── frontend/                      # Angular SPA (built assets)
    └── static/                    # Compiled Angular output
```

---

## 3. Data Model (Entity Relationship)

### Core Entities
```
User ──────────────── Role ──────────────── Permission
  |                      |                       |
  |                      |                       |
  +── owns ──> Document  +── ACL ──> ANY MODEL   |
  |              |                               |
  |              +── has ──> DocumentFile         |
  |              +── has ──> DocumentVersion      |
  |              +── has ──> DocumentPage         |
  |              +── type ──> DocumentType ──> RetentionPolicy
  |              +── has ──> Tag (M2M, hierarchical)
  |              +── has ──> Correspondent
  |              +── in ──> Cabinet (M2M, hierarchical)
  |              +── has ──> CustomFieldInstance
  |              +── has ──> Comment
  |              +── has ──> ShareLink
  |              +── has ──> WorkflowInstance
  |              +── has ──> AuditLogEntry
  |
  +── has ──> SavedView
  +── has ──> Notification
  +── has ──> Quota
```

### Key Design Decisions

#### Soft Deletes
All major models inherit from `SoftDeleteModel`:
```python
class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        abstract = True

    objects = SoftDeleteManager()      # Excludes deleted
    all_objects = models.Manager()     # Includes deleted
```

#### Auditable Models
All models that need audit trails inherit from `AuditableModel`:
```python
class AuditableModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, null=True, related_name='+')
    updated_by = models.ForeignKey(User, null=True, related_name='+')

    class Meta:
        abstract = True
```

#### Owned Models
Models with ownership semantics:
```python
class OwnedModel(models.Model):
    owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    class Meta:
        abstract = True
```

---

## 4. Processing Pipeline Architecture

### Plugin Chain
```python
class ProcessingPipeline:
    """Orchestrates document processing via plugin chain."""

    plugins = [
        PreflightPlugin,           # Order 10
        BarcodePlugin,             # Order 20
        WorkflowTriggerPlugin,     # Order 30
        PreConsumeHookPlugin,      # Order 40
        ParserPlugin,              # Order 50
        OCRPlugin,                 # Order 60
        TextExtractionPlugin,      # Order 70
        LanguageDetectionPlugin,   # Order 80
        DateExtractionPlugin,      # Order 90
        ClassificationPlugin,      # Order 100
        AIPlugin,                  # Order 110
        IndexPlugin,               # Order 120
        ThumbnailPlugin,           # Order 130
        PostConsumeHookPlugin,     # Order 140
    ]

    def process(self, context: ProcessingContext) -> ProcessingResult:
        for plugin_class in self.plugins:
            plugin = plugin_class()
            if plugin.can_run(context):
                plugin.setup(context)
                try:
                    result = plugin.process(context)
                    if result.should_stop:
                        break
                finally:
                    plugin.cleanup(context)
        return context.result
```

### Processing Context
```python
@dataclass
class ProcessingContext:
    # Input
    source_path: Path
    original_filename: str
    mime_type: str
    source_type: str  # web, api, email, folder, scanner

    # Accumulated state
    content: str = ""
    language: str = ""
    date_created: date = None
    title: str = ""
    archive_path: Path = None
    thumbnail_path: Path = None
    page_count: int = 0
    checksum: str = ""
    barcode_data: dict = field(default_factory=dict)

    # Classification suggestions
    suggested_tags: list = field(default_factory=list)
    suggested_correspondent: int = None
    suggested_document_type: int = None
    suggested_storage_path: int = None

    # Overrides (from workflow rules or API)
    override_title: str = None
    override_correspondent: int = None
    override_document_type: int = None
    override_tags: list = None
    override_owner: int = None

    # Progress tracking
    task_id: str = None
    progress: float = 0.0
    status_message: str = ""
```

---

## 5. Security Architecture

### Authentication Flow
```
Client Request
    |
    v
[Nginx/Caddy Reverse Proxy]
    |
    v
[Django Middleware Stack]
    |
    +-- SessionAuthentication (cookie-based, web UI)
    +-- TokenAuthentication (API clients)
    +-- OAuth2Authentication (SSO providers)
    +-- LDAPAuthentication (enterprise)
    |
    v
[Permission Check]
    |
    +-- Model-level permissions (DRF)
    +-- Object-level ACLs (django-guardian + custom)
    +-- Owner check
    |
    v
[Response with filtered data]
```

### Permission Resolution Order
1. Superuser bypasses all checks
2. Check model-level permissions (can user access this model at all?)
3. Check object ownership (owner has full access)
4. Check explicit ACLs (role + permission + object)
5. Check group-inherited permissions
6. Default: deny

### Encryption Architecture
```
Document Upload
    |
    v
[Checksum Calculation (SHA-256)]
    |
    v
[Storage Backend Selection]
    |
    +-- Encrypted Backend?
    |       |
    |       v
    |   [AES-256-CBC Encryption]
    |       - Random IV per file
    |       - PBKDF2 key derivation
    |       - Chunked encryption
    |       |
    |       v
    |   [Encrypted file stored]
    |
    +-- Standard Backend?
            |
            v
        [File stored as-is]
```

---

## 6. Celery Task Architecture

### Task Queues
| Queue | Purpose | Workers |
|-------|---------|---------|
| `default` | General tasks | 2 |
| `processing` | Document consumption, OCR | 4 |
| `ml` | ML training, AI operations | 1 |
| `search` | Index updates, search operations | 2 |
| `mail` | Email fetching | 1 |
| `workflow` | Workflow execution | 2 |
| `notifications` | Email/webhook delivery | 1 |

### Beat Schedule
```python
CELERY_BEAT_SCHEDULE = {
    "process_mail": {
        "task": "sources.tasks.process_mail_accounts",
        "schedule": crontab(minute="*/10"),
    },
    "train_classifier": {
        "task": "ml.tasks.train_classifier",
        "schedule": crontab(minute=5, hour="*/1"),
    },
    "optimize_index": {
        "task": "search.tasks.optimize_index",
        "schedule": crontab(hour=0, minute=0),
    },
    "check_workflows": {
        "task": "workflows.tasks.check_scheduled_workflows",
        "schedule": crontab(minute="*/15"),
    },
    "process_escalations": {
        "task": "workflows.tasks.process_escalations",
        "schedule": crontab(minute="*/5"),
    },
    "cleanup_trash": {
        "task": "documents.tasks.cleanup_trash",
        "schedule": crontab(hour=2, minute=0),
    },
    "update_ai_index": {
        "task": "ml.tasks.update_vector_index",
        "schedule": crontab(hour=3, minute=0),
    },
    "sanity_check": {
        "task": "documents.tasks.sanity_check",
        "schedule": crontab(hour=4, minute=0),
    },
}
```

---

## 7. Search Architecture

### Dual Search Strategy
```
User Query
    |
    +--- Keyword Search (Elasticsearch)
    |       |
    |       +-- Full-text match (BM25 scoring)
    |       +-- Field-specific queries
    |       +-- Faceted aggregations
    |       +-- Date range queries
    |       +-- Permission filtering
    |       |
    |       v
    |   Ranked Results (by relevance)
    |
    +--- Semantic Search (FAISS)
            |
            +-- Query embedding (same model as docs)
            +-- Cosine similarity search
            +-- K-nearest neighbors
            |
            v
        Similar Documents (by meaning)
```

### Elasticsearch Index Schema
```json
{
    "mappings": {
        "properties": {
            "id": { "type": "integer" },
            "title": { "type": "text", "analyzer": "standard" },
            "content": { "type": "text", "analyzer": "standard" },
            "correspondent": { "type": "text" },
            "correspondent_id": { "type": "integer" },
            "document_type": { "type": "text" },
            "document_type_id": { "type": "integer" },
            "tags": { "type": "keyword" },
            "tag_ids": { "type": "integer" },
            "cabinets": { "type": "keyword" },
            "asn": { "type": "integer" },
            "created": { "type": "date" },
            "added": { "type": "date" },
            "modified": { "type": "date" },
            "owner_id": { "type": "integer" },
            "checksum": { "type": "keyword" },
            "original_filename": { "type": "text" },
            "page_count": { "type": "integer" },
            "custom_fields": { "type": "object", "dynamic": true },
            "notes": { "type": "text" },
            "storage_path": { "type": "text" },
            "language": { "type": "keyword" },
            "mime_type": { "type": "keyword" }
        }
    }
}
```

---

## 8. Deployment Architecture

### Docker Compose (Development/Small Deployment)
```yaml
services:
  app:
    image: docvault/docvault:latest
    depends_on: [postgres, redis, elasticsearch]
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
      - ELASTICSEARCH_URL=http://elasticsearch:9200
      - STORAGE_BACKEND=s3
      - S3_ENDPOINT=http://minio:9000
    volumes:
      - media:/app/media
      - consume:/app/consume

  worker:
    image: docvault/docvault:latest
    command: celery -A docvault worker
    depends_on: [postgres, redis, elasticsearch]

  beat:
    image: docvault/docvault:latest
    command: celery -A docvault beat
    depends_on: [postgres, redis]

  postgres:
    image: postgres:16-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  elasticsearch:
    image: elasticsearch:8.15.0
    volumes:
      - esdata:/usr/share/elasticsearch/data

  minio:
    image: minio/minio:latest
    volumes:
      - s3data:/data
```

### Kubernetes (Production)
- Helm chart with configurable values
- Horizontal Pod Autoscaler for workers
- PersistentVolumeClaims for data
- Ingress with TLS
- ConfigMaps and Secrets for configuration
- Health/readiness probes

---

## 9. Monitoring & Observability

### Health Endpoints
- `GET /health/` - Application health (DB, Redis, Elasticsearch)
- `GET /ready/` - Readiness check (all services connected)
- `GET /metrics/` - Prometheus metrics

### Key Metrics
- Document processing rate (docs/minute)
- OCR processing time (p50, p95, p99)
- Search query latency
- Task queue depth
- Active users
- Storage utilization
- Error rates by type

### Logging
- Structured JSON logging
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Correlation IDs for request tracing
- Separate logs for: application, celery, access, audit

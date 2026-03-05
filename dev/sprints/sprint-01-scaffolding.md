# Sprint 1: Project Scaffolding & Core Models

## Phase: 1 - Foundation
## Duration: 2 weeks
## Prerequisites: None (first sprint)

---

## Sprint Goal
Establish the project foundation: Django project with modular structure, core base models, the Document data model hierarchy, PostgreSQL setup, Docker Compose for development, and environment-based configuration.

---

## Context for Agents

### Architecture Reference
- Read `/doc/architecture.md` for the full module layout
- Read `/doc/product-spec.md` Section 2 for system architecture overview
- This sprint establishes the directory structure that all future sprints build upon

### Key Design Decisions
1. **Modular monolith**: Single Django project with clearly separated apps (NOT microservices, NOT 100+ apps)
2. **Base model classes**: All models inherit from core abstract models for consistency
3. **PostgreSQL primary**: SQLite for dev convenience, PostgreSQL for production
4. **Environment-based config**: All settings via environment variables (12-factor app)

---

## Tasks

### Task 1.1: Django Project Initialization
**Priority**: Critical
**Estimated Effort**: 4 hours

Create the Django project with the following structure:
```
docvault/
├── manage.py
├── pyproject.toml              # Python project config (uv/pip)
├── requirements/
│   ├── base.txt                # Core dependencies
│   ├── dev.txt                 # Development extras
│   └── test.txt                # Testing extras
├── docvault/                   # Project configuration
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py         # Settings loader
│   │   ├── base.py             # Base settings
│   │   ├── development.py      # Dev overrides
│   │   └── production.py       # Production overrides
│   ├── urls.py                 # Root URL configuration
│   ├── wsgi.py                 # WSGI entry point
│   └── asgi.py                 # ASGI entry point (for future Channels)
├── core/                       # Core utilities app
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── managers.py
│   └── tests/
├── documents/                  # Documents app
│   ├── __init__.py
│   ├── apps.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── document.py
│   │   ├── document_type.py
│   │   └── page.py
│   ├── admin.py
│   ├── tests/
│   └── migrations/
└── .env.example                # Example environment file
```

**Acceptance Criteria**:
- `python manage.py check` passes with no errors
- `python manage.py runserver` starts successfully
- Settings load from environment variables
- Django admin accessible at `/admin/`

### Task 1.2: Core Base Models
**Priority**: Critical
**Estimated Effort**: 6 hours

Create abstract base models in `core/models.py`:

```python
# SoftDeleteModel - soft deletion with trash support
class SoftDeleteModel(models.Model):
    deleted_at = DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        abstract = True

    objects = SoftDeleteManager()     # Filters out deleted
    all_objects = models.Manager()    # Includes deleted

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])

    @property
    def is_deleted(self):
        return self.deleted_at is not None
```

```python
# AuditableModel - automatic timestamp and actor tracking
class AuditableModel(models.Model):
    created_at = DateTimeField(auto_now_add=True, db_index=True)
    updated_at = DateTimeField(auto_now=True)
    created_by = ForeignKey(User, null=True, blank=True,
                           on_delete=SET_NULL, related_name='+')
    updated_by = ForeignKey(User, null=True, blank=True,
                           on_delete=SET_NULL, related_name='+')

    class Meta:
        abstract = True
```

```python
# OwnedModel - ownership semantics
class OwnedModel(models.Model):
    owner = ForeignKey(User, null=True, blank=True,
                      on_delete=SET_NULL, related_name='+')

    class Meta:
        abstract = True
```

Create `SoftDeleteManager` in `core/managers.py`:
```python
class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)
```

**Acceptance Criteria**:
- All three base models are abstract and can be inherited
- SoftDeleteManager correctly filters deleted records
- `soft_delete()` sets `deleted_at`, `restore()` clears it
- `all_objects` manager returns both deleted and non-deleted records
- Unit tests verify all base model behavior

### Task 1.3: Document Models
**Priority**: Critical
**Estimated Effort**: 8 hours

Create document models in `documents/models/`:

**`document_type.py`**:
```python
class DocumentType(AuditableModel, OwnedModel):
    name = CharField(max_length=128, unique=True)
    slug = SlugField(max_length=128, unique=True)

    # Retention policies (from Mayan EDMS)
    trash_time_period = PositiveIntegerField(null=True, blank=True)
    trash_time_unit = CharField(max_length=16, choices=TIME_UNITS, null=True)
    delete_time_period = PositiveIntegerField(null=True, blank=True)
    delete_time_unit = CharField(max_length=16, choices=TIME_UNITS, null=True)

    # Matching (from Paperless-ngx)
    match = CharField(max_length=256, blank=True, default='')
    matching_algorithm = PositiveSmallIntegerField(
        choices=MATCHING_ALGORITHMS, default=MATCH_NONE
    )
    is_insensitive = BooleanField(default=True)
```

**`document.py`**:
```python
class Document(SoftDeleteModel, AuditableModel, OwnedModel):
    # Identity
    uuid = UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = CharField(max_length=128, db_index=True)
    content = TextField(blank=True, default='')  # OCR text

    # Classification
    document_type = ForeignKey(DocumentType, null=True, blank=True,
                              on_delete=SET_NULL)
    correspondent = ForeignKey('organization.Correspondent', null=True,
                              blank=True, on_delete=SET_NULL)
    storage_path = ForeignKey('organization.StoragePath', null=True,
                             blank=True, on_delete=SET_NULL)
    tags = ManyToManyField('organization.Tag', blank=True)

    # File info
    original_filename = CharField(max_length=1024, blank=True, default='')
    mime_type = CharField(max_length=256, blank=True, default='')
    checksum = CharField(max_length=64, blank=True, default='')
    archive_checksum = CharField(max_length=64, blank=True, default='')
    page_count = PositiveIntegerField(default=0)

    # Storage
    filename = FilePathField(max_length=1024, unique=True, null=True)
    archive_filename = FilePathField(max_length=1024, unique=True, null=True)

    # Dates
    created = DateField(default=date.today, db_index=True)  # Document date
    added = DateTimeField(default=timezone.now, db_index=True)  # Ingestion date

    # Archive Serial Number (from Paperless-ngx)
    archive_serial_number = PositiveIntegerField(
        unique=True, null=True, blank=True
    )

    # Versioning
    root_document = ForeignKey('self', null=True, blank=True,
                              on_delete=SET_NULL, related_name='versions')
    version_label = CharField(max_length=64, blank=True, default='')

    # Language
    language = CharField(max_length=16, default='en')

    class Meta:
        ordering = ['-created']
        indexes = [
            models.Index(fields=['checksum']),
            models.Index(fields=['archive_serial_number']),
        ]


class DocumentFile(AuditableModel):
    """Physical file artifact (from Mayan EDMS multi-file support)."""
    document = ForeignKey(Document, on_delete=CASCADE, related_name='files')
    file = FileField(upload_to='documents/files/')
    filename = CharField(max_length=1024)
    mime_type = CharField(max_length=256)
    encoding = CharField(max_length=64, blank=True, default='')
    checksum = CharField(max_length=64)
    size = PositiveBigIntegerField(default=0)
    comment = TextField(blank=True, default='')

    class Meta:
        ordering = ['-created_at']


class DocumentVersion(AuditableModel):
    """Version tracking (from Mayan EDMS)."""
    document = ForeignKey(Document, on_delete=CASCADE, related_name='version_history')
    version_number = PositiveIntegerField()
    comment = TextField(blank=True, default='')
    is_active = BooleanField(default=False)
    file = ForeignKey(DocumentFile, null=True, on_delete=SET_NULL)

    class Meta:
        ordering = ['-version_number']
        unique_together = [['document', 'version_number']]
```

**`page.py`**:
```python
class DocumentPage(models.Model):
    """Page-level content (from Mayan EDMS)."""
    document = ForeignKey(Document, on_delete=CASCADE, related_name='pages')
    page_number = PositiveIntegerField()
    content = TextField(blank=True, default='')  # OCR text for this page

    class Meta:
        ordering = ['page_number']
        unique_together = [['document', 'page_number']]
```

**Acceptance Criteria**:
- All models have proper migrations
- `python manage.py migrate` runs without errors
- Django admin shows all models with basic CRUD
- ForeignKey relationships work correctly
- Soft delete works on Document model
- Unique constraints enforced (UUID, checksum, ASN, version_number)
- Unit tests for model creation, soft delete, version ordering

### Task 1.4: Docker Compose Development Environment
**Priority**: High
**Estimated Effort**: 4 hours

Create `docker-compose.yml` for development:
```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: docvault
      POSTGRES_USER: docvault
      POSTGRES_PASSWORD: docvault
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

Create `.env.example`:
```bash
# Database
DATABASE_URL=postgresql://docvault:docvault@localhost:5432/docvault

# Redis
REDIS_URL=redis://localhost:6379

# Django
DJANGO_SECRET_KEY=change-me-in-production
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Storage
MEDIA_ROOT=./media
STATIC_ROOT=./static
```

Create `Dockerfile` for the Django application:
```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/base.txt

# Copy application
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "docvault.wsgi:application", "--bind", "0.0.0.0:8000"]
```

**Acceptance Criteria**:
- `docker compose up db redis` starts PostgreSQL and Redis
- Application connects to PostgreSQL when `DATABASE_URL` is set
- Application falls back to SQLite when `DATABASE_URL` is not set
- `.env.example` documents all required environment variables
- `Dockerfile` builds successfully

### Task 1.5: Settings Management
**Priority**: High
**Estimated Effort**: 4 hours

Implement settings in `docvault/settings/`:

**`base.py`** key sections:
- Database configuration (PostgreSQL via `DATABASE_URL` or individual vars)
- Redis configuration (`REDIS_URL`)
- Installed apps (core, documents)
- Middleware stack
- Static/media file configuration
- Timezone and language settings
- Logging configuration (structured JSON)

**`development.py`** overrides:
- DEBUG = True
- Django Debug Toolbar (optional)
- Console email backend
- Relaxed security settings

**`production.py`** overrides:
- DEBUG = False
- Security middleware enabled
- Proper ALLOWED_HOSTS
- Secure cookies
- HSTS headers

**Acceptance Criteria**:
- `DJANGO_SETTINGS_MODULE` selects environment
- All sensitive values come from environment variables
- No secrets in source code
- Logging outputs structured JSON

### Task 1.6: Basic Django Admin Configuration
**Priority**: Medium
**Estimated Effort**: 2 hours

Register all models in Django admin with useful displays:

```python
# documents/admin.py
@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'document_type', 'created', 'mime_type', 'owner']
    list_filter = ['document_type', 'mime_type', 'created']
    search_fields = ['title', 'content', 'original_filename']
    readonly_fields = ['uuid', 'checksum', 'created_at', 'updated_at']

@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'trash_time_period', 'delete_time_period']
    prepopulated_fields = {'slug': ('name',)}
```

**Acceptance Criteria**:
- All models visible in Django admin
- Useful list displays, filters, and search
- Admin is functional for data inspection during development

---

## Dependencies

### Python Packages (requirements/base.txt)
```
Django>=5.2,<5.3
psycopg[binary]>=3.3,<4
django-environ>=0.12
gunicorn>=25.0
```

### Python Packages (requirements/dev.txt)
```
-r base.txt
pytest>=8.0
pytest-django>=4.8
factory-boy>=3.3
django-debug-toolbar>=5.0
```

---

## Definition of Done
- [ ] Django project runs with `python manage.py runserver`
- [ ] All models have migrations and migrate successfully
- [ ] Core base models (SoftDelete, Auditable, Owned) have unit tests
- [ ] Document models (Document, DocumentType, DocumentFile, DocumentVersion, DocumentPage) have unit tests
- [ ] Docker Compose starts PostgreSQL and Redis
- [ ] Application connects to PostgreSQL or falls back to SQLite
- [ ] Django admin shows all models
- [ ] Settings load from environment variables
- [ ] No secrets in source code
- [ ] `python manage.py test` passes all tests

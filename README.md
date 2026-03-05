# DocVault

The ultimate open-source document management system. Ingest, organize, search, and collaborate on documents with OCR, AI-powered search, workflows, e-signatures, and more.

## Features

### Document Management
- **Upload & Ingest** - Drag-and-drop, email import (IMAP/POP3), watch folders, public contributor portals
- **OCR Processing** - Tesseract + ocrmypdf with deskew, rotation, and PDF/A output
- **Zone OCR** - Template-based field extraction for structured documents (invoices, forms)
- **Versioning** - Full document version history with check-out/check-in locking
- **Barcode Detection** - 1D/2D barcode scanning with separator page support and ASN assignment

### Organization & Metadata
- **Tags** - Hierarchical tagging with color coding and auto-assignment via pattern matching
- **Cabinets** - Tree-structured folder organization
- **Correspondents** - Sender/recipient classification with auto-matching
- **Custom Fields** - 12 data types (string, date, monetary, document links, select, etc.)
- **Document Types** - Classification schemas with retention policies
- **Storage Paths** - Jinja2-templated file organization on disk

### Search & Discovery
- **Full-Text Search** - Elasticsearch-backed with faceted filtering
- **Semantic Search** - AI-powered vector similarity via embeddings (FAISS)
- **Hybrid Search** - Combined text + semantic ranking
- **Saved Views** - Reusable search configurations with dashboard/sidebar pinning
- **Autocomplete** - Real-time search suggestions
- **Search Analytics** - Query tracking, click-through analysis, synonyms, and curations

### AI & Machine Learning
- **LLM Integration** - OpenAI (GPT-4o) or Ollama (local) for document chat, summarization, entity extraction, and title suggestions
- **ML Classification** - Scikit-learn document classifier with training pipeline
- **Named Entity Recognition** - SpaCy-based extraction of people, organizations, locations, dates
- **Vector Embeddings** - FAISS index for similarity search and document clustering

### Collaboration
- **Comments** - Threaded markdown comments on documents
- **Annotations** - Visual annotations (highlights, sticky notes, text boxes, stamps) with replies
- **Share Links** - Password-protected public access with expiration and download tracking
- **Check-Out / Check-In** - Document locking to prevent concurrent edits

### Workflows
- **State Machines** - Configurable document lifecycle with states, transitions, and conditions
- **Automation Rules** - Auto-launch workflows based on document type or trigger events
- **Escalations** - Time-based automatic state transitions
- **State Actions** - Pluggable actions on entry/exit with Python expression conditions

### E-Signatures
- **Signature Requests** - Sequential or parallel signing workflows with expiration
- **Public Signing** - Token-based signing without authentication
- **Signature Fields** - Signature, initials, date, checkbox, and text fields with page coordinates
- **Audit Trail** - Complete event log with IP address and user agent tracking

### Security & Compliance
- **Authentication** - Username/password, OIDC, LDAP, social auth (django-allauth)
- **Two-Factor Auth** - TOTP-based 2FA with QR code setup and backup codes
- **Object Permissions** - Per-document access control via django-guardian
- **Role-Based Access** - Custom roles with granular permission sets
- **GPG Signing** - Cryptographic document signing and verification
- **Encryption at Rest** - Optional AES storage encryption with configurable KDF
- **Audit Logging** - Comprehensive action logging for compliance
- **Legal Hold** - Document preservation with custodian notification and acknowledgment
- **IP Access Control** - Configurable whitelist/blacklist
- **Security Headers** - HSTS, X-Frame-Options, CSP, XSS protection

### Physical Records
- **Location Tracking** - Hierarchical physical locations (building > room > cabinet > shelf > box)
- **Charge-Out Management** - Check-out/check-in with expected return dates and overdue tracking
- **Barcode Checkout** - Scan-based physical document checkout
- **Destruction Certificates** - Documented destruction with witness and certificate PDF

### Contributor Portal
- **Public Upload Portal** - Branded portals for external document submission (no auth required)
- **Document Requests** - Token-based document requests with deadlines and reminders
- **Submission Review** - Admin review workflow for incoming portal submissions

### Notifications
- **Real-Time** - WebSocket-based push notifications via Django Channels
- **Preferences** - Per-event-type notification settings (in-app, email, webhook)
- **Quota Management** - Document and storage usage quotas per user/group

### Document Relationships
- **Relationship Types** - Configurable link types (supersedes, references, related, etc.)
- **Graph Visualization** - Visual document relationship graph

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Django 5.2, Django REST Framework 3.16, Django Channels 4.2 |
| **Frontend** | Angular 21, Bootstrap 5.3, TypeScript 5.9 |
| **Database** | PostgreSQL 16 |
| **Search** | Elasticsearch 8 (optional) |
| **Cache / Broker** | Redis 7 |
| **Task Queue** | Celery 5.6 |
| **Object Storage** | Local filesystem or S3/Minio |
| **OCR** | Tesseract, ocrmypdf 16 |
| **AI/ML** | OpenAI / Ollama, SpaCy 3.7, Scikit-learn 1.7, FAISS |
| **Auth** | django-allauth, django-guardian, mozilla-django-oidc, PyOTP |
| **API Docs** | drf-spectacular (OpenAPI 3 / Swagger UI) |

---

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 22+ (for frontend)
- PostgreSQL 16+
- Redis 7+

### Development Setup

```bash
# Clone the repository
git clone git@github.com:packetloss404/docvault.git
cd docvault

# Backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements/dev.txt
cp .env.example .env  # Edit with your settings
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# Frontend (in a separate terminal)
cd src-ui
npm install
ng serve
```

The API will be available at `http://localhost:8000` and the frontend at `http://localhost:4200`.

### Docker Compose

```bash
cp .env.example .env
docker compose up -d
```

This starts all services:
- **web** - Django/Gunicorn on port 8000
- **worker** - Celery worker (default + processing queues)
- **db** - PostgreSQL 16
- **redis** - Redis 7
- **minio** - S3-compatible object storage

---

## Configuration

Configuration is managed via environment variables. See [`.env.example`](.env.example) for the full list.

### Core Settings

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://docvault:docvault@localhost:5432/docvault` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string |
| `DJANGO_SECRET_KEY` | — | **Required.** Django secret key |
| `DJANGO_DEBUG` | `false` | Enable debug mode |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `DJANGO_SETTINGS_MODULE` | `docvault.settings.development` | Settings module (`development`, `production`, `testing`) |

### Storage

| Variable | Default | Description |
|---|---|---|
| `STORAGE_BACKEND` | `local` | `local` or `s3` |
| `MEDIA_ROOT` | `./media` | Local media directory |
| `S3_ENDPOINT_URL` | — | S3/Minio endpoint |
| `S3_ACCESS_KEY` | — | S3 access key |
| `S3_SECRET_KEY` | — | S3 secret key |
| `S3_BUCKET_NAME` | — | S3 bucket name |
| `STORAGE_ENCRYPTION_ENABLED` | `false` | Enable AES encryption at rest |

### OCR

| Variable | Default | Description |
|---|---|---|
| `OCR_LANGUAGE` | `eng` | Tesseract language(s) |
| `OCR_MODE` | `skip` | `skip` / `redo` / `force` |
| `OCR_IMAGE_DPI` | `300` | Processing DPI |
| `OCR_DESKEW` | `true` | Auto-deskew pages |
| `OCR_ROTATE` | `true` | Auto-rotate pages |

### AI / LLM

| Variable | Default | Description |
|---|---|---|
| `LLM_ENABLED` | `false` | Enable LLM features |
| `LLM_PROVIDER` | `openai` | `openai` or `ollama` |
| `LLM_MODEL` | `gpt-4o-mini` | Model name |
| `LLM_API_KEY` | — | API key (OpenAI) |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |

### Search

| Variable | Default | Description |
|---|---|---|
| `ELASTICSEARCH_ENABLED` | `false` | Enable Elasticsearch |
| `ELASTICSEARCH_URL` | `http://localhost:9200` | Elasticsearch URL |

### Security

| Variable | Default | Description |
|---|---|---|
| `OIDC_ENABLED` | `false` | Enable OpenID Connect |
| `LDAP_ENABLED` | `false` | Enable LDAP authentication |
| `SESSION_COOKIE_AGE` | `3600` | Session timeout (seconds) |
| `IP_WHITELIST` | — | Allowed IP addresses |
| `SENTRY_DSN` | — | Sentry error tracking DSN |

---

## API

Interactive API documentation is available at `/api/docs/` (Swagger UI) when the server is running.

All endpoints are under `/api/v1/`. Key endpoint groups:

| Endpoint | Description |
|---|---|
| `/api/v1/auth/` | Login, register, profile, 2FA, tokens |
| `/api/v1/documents/` | Document CRUD, upload, types |
| `/api/v1/tags/`, `/correspondents/`, `/cabinets/` | Organization |
| `/api/v1/custom-fields/` | Dynamic metadata fields |
| `/api/v1/search/` | Full-text, autocomplete, analytics |
| `/api/v1/ai/` | Semantic search, chat, summarize, entity extraction |
| `/api/v1/workflow-templates/` | Workflow management |
| `/api/v1/signature-requests/` | E-signature workflows |
| `/api/v1/legal-holds/` | Document preservation |
| `/api/v1/physical-locations/`, `/physical-records/` | Physical record tracking |
| `/api/v1/portals/` | Contributor portal management |
| `/api/v1/sources/`, `/mail-accounts/` | Document ingestion sources |
| `/api/v1/notifications/` | Real-time notifications |
| `/api/v1/zone-ocr-templates/` | Zone OCR configuration |
| `/api/v1/entities/` | Named entity recognition |
| `/api/v1/audit-log/` | Compliance audit trail |
| `/health/`, `/ready/`, `/metrics/` | Observability |

---

## Deployment

### Production Docker

```bash
docker build -f Dockerfile.production -t docvault:latest .
```

The production image uses a multi-stage build (Node.js frontend + Python backend), runs as non-root (UID 1000), and includes health checks.

### Kubernetes / Helm

```bash
cd deploy/helm
helm dependency update docvault
helm install docvault docvault/ -f docvault/values.yaml
```

The Helm chart deploys:
- **Web** - Gunicorn (2 replicas, 1 CPU / 1Gi RAM limit)
- **Worker** - Celery (2 replicas, default + processing queues)
- **Beat** - Celery beat scheduler (1 replica)
- **PostgreSQL** - Bitnami subchart
- **Redis** - Bitnami subchart
- **PVC** - 10Gi ReadWriteMany for media storage
- **Ingress** - Nginx (optional)

---

## Development

### Running Tests

```bash
pytest
```

Tests use SQLite, eager Celery execution, and fast password hashing for speed.

### Code Quality

```bash
ruff check .    # Linting
ruff format .   # Formatting
```

Ruff is configured with a 120-character line length targeting Python 3.12+.

### Project Structure

```
docvault/
├── ai/                  # LLM integration (chat, embeddings, semantic search)
├── annotations/         # Visual document annotations
├── collaboration/       # Comments, checkout, share links
├── core/                # Base models, health checks, bulk operations
├── deploy/              # Helm charts, Kubernetes manifests
├── documents/           # Core document models and API
├── docvault/            # Django project settings and config
├── entities/            # Named entity recognition
├── esignatures/         # E-signature workflows
├── legal_hold/          # Legal hold for compliance
├── ml/                  # ML classification pipeline
├── notifications/       # WebSocket notifications, quotas
├── organization/        # Tags, cabinets, correspondents, custom fields
├── physical_records/    # Physical document tracking
├── portal/              # Public contributor portal
├── processing/          # OCR, barcode detection, task management
├── relationships/       # Document relationships and graph
├── search/              # Full-text search, saved views, analytics
├── security/            # Auth, audit logging, GPG, 2FA
├── sources/             # Email, watch folder ingestion
├── src-ui/              # Angular frontend
├── storage/             # Storage backends, deduplication
├── workflows/           # State machine workflows
└── zone_ocr/            # Template-based field extraction
```

---

## License

This project is licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.en.html).

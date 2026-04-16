# DocVault

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Angular 21](https://img.shields.io/badge/Angular-21-red.svg)](https://angular.dev)
[![Django 5.2](https://img.shields.io/badge/Django-5.2-green.svg)](https://www.djangoproject.com)
[![Tests: 1,554](https://img.shields.io/badge/tests-1%2C554%20passing-brightgreen.svg)]()

The ultimate open-source document management system. Ingest, organize, search, and collaborate on documents with OCR, AI-powered search, workflows, e-signatures, and more.

---

## Features

### Document Management
- **Upload & Ingest** — Drag-and-drop, email import (IMAP/POP3), watch folders, S3 buckets, public contributor portals
- **OCR Processing** — Tesseract + ocrmypdf with deskew, rotation, and PDF/A output
- **Zone OCR** — Template-based field extraction for structured documents (invoices, forms) with perceptual similarity scoring
- **Versioning** — Full version history with side-by-side diff comparison and check-out/check-in locking
- **Barcode Detection** — 1D/2D barcode scanning with separator page support, ASN assignment, and printable label generation

### Organization & Metadata
- **Tags** — Hierarchical tagging (max 5 levels) with color coding and auto-assignment via pattern matching
- **Cabinets** — Tree-structured folder organization with drag-and-drop reorder
- **Correspondents** — Sender/recipient classification with auto-matching
- **Custom Fields** — 12 data types (string, date, monetary, document links, select, etc.) with document type assignments
- **Document Types** — Classification schemas with custom field editor and retention policies
- **Storage Paths** — Jinja2-templated file organization with autocomplete

### Search & Discovery
- **Full-Text Search** — Elasticsearch-backed with faceted filtering and entity facets
- **Semantic Search** — AI-powered vector similarity via embeddings (FAISS)
- **Hybrid Search** — Combined text + semantic ranking
- **Global Search** — Ctrl+K / Cmd+K command palette with cross-entity typeahead and recent queries
- **Rich Filter Builder** — Field/operator/value filter rows on the search page
- **Saved Views** — Reusable search configurations with OR filter groups and dashboard/sidebar pinning
- **Search Analytics** — Automatic query logging, click-through tracking, response-time metrics, synonyms, and curations

### AI & Machine Learning
- **LLM Integration** — OpenAI, Azure OpenAI, or Ollama (local) for document chat, summarization, entity extraction, and title suggestions
- **ML Classification** — Scikit-learn document classifier with training pipeline and suggested field persistence
- **Named Entity Recognition** — SpaCy-based extraction with entity co-occurrence visualization
- **Vector Embeddings** — FAISS index for similarity search and document clustering
- **Redis-Backed Caching** — Stem cache for ML preprocessing performance

### Collaboration
- **Comments** — Threaded comments on documents with edit/delete
- **Annotations** — Visual annotations (highlights, sticky notes, text boxes, stamps) with replies, integrated into document preview
- **Share Links** — Password-protected public access with expiration and download tracking
- **Check-Out / Check-In** — Document locking to prevent concurrent edits

### Workflows
- **State Machines** — Configurable document lifecycle with states, transitions, and conditions
- **Transition Fields** — Collect data during transitions (text, integer, date, boolean, select)
- **Automation Rules** — Auto-launch workflows based on triggers (consumption, creation, update, scheduled)
- **Escalations** — Time-based automatic state transitions via Celery Beat
- **State Actions** — Pluggable actions on entry/exit (set tags, send email, webhook, launch workflow)

### E-Signatures
- **Signature Requests** — Sequential or parallel signing workflows with expiration
- **Public Signing** — Token-based signing without authentication
- **External Signer Verification** — Code-based identity verification for external parties
- **Signature Fields** — Signature, initials, date, checkbox, and text fields with page coordinates
- **GPG Signing** — Cryptographic document signing and verification
- **Audit Trail** — Complete event log with IP address and user agent tracking

### Security & Compliance
- **Authentication** — Username/password, OIDC/SSO, LDAP, social auth (django-allauth)
- **Two-Factor Auth** — TOTP-based 2FA with QR code setup and backup codes
- **RBAC** — Admin UI for users, groups, roles, and permissions with role-based navigation visibility
- **Object Permissions** — Per-document access control via django-guardian
- **GPG Signing** — Cryptographic document signing and verification
- **Encryption at Rest** — Optional AES storage encryption with configurable KDF
- **Audit Logging** — Comprehensive action logging with CSV/JSON export
- **Legal Hold** — Document preservation with mutation blocking (HTTP 409), custodian notification, and acknowledgment
- **Content-Addressed Storage** — Deduplication with integrity verification and CAS migration command
- **IP Access Control** — Configurable whitelist/blacklist
- **Security Headers** — HSTS, X-Frame-Options, CSP, XSS protection

### Physical Records
- **Location Tracking** — Hierarchical physical locations (building > room > cabinet > shelf > box)
- **Charge-Out Management** — Check-out/check-in with expected return dates and overdue tracking
- **Barcode Checkout** — Scan-based physical document checkout
- **Destruction Certificates** — Documented destruction with witness and certificate PDF

### Contributor Portal
- **Public Upload Portal** — Branded portals for external document submission (no auth required)
- **Document Requests** — Token-based document requests with deadlines and reminders
- **Submission Review** — Admin review workflow for incoming portal submissions

### Notifications
- **Real-Time** — WebSocket-based push notifications via Django Channels with auto-reconnect
- **Preferences** — Per-event-type notification settings (in-app, email, webhook)
- **Quota Management** — Document and storage usage quotas per user/group

### Document Relationships
- **Relationship Types** — Configurable link types (supersedes, references, related, etc.)
- **Supersession Tracking** — Automatic `is_obsolete` marking when documents are superseded
- **Graph Visualization** — Visual document relationship graph

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Django 5.2, Django REST Framework 3.16, Django Channels 4.2 |
| **Frontend** | Angular 21, Bootstrap 5.3, TypeScript 5.9 |
| **Database** | PostgreSQL 16 (SQLite for local dev) |
| **Search** | Elasticsearch 8 (optional) |
| **Cache / Broker** | Redis 7 |
| **Task Queue** | Celery 5.6 with Beat scheduler |
| **Object Storage** | Local filesystem or S3/MinIO |
| **OCR** | Tesseract, ocrmypdf 16 |
| **AI/ML** | OpenAI / Azure OpenAI / Ollama, SpaCy 3.7, Scikit-learn 1.7, FAISS |
| **Auth** | django-allauth, django-guardian, PyOTP |
| **API Docs** | drf-spectacular (OpenAPI 3 / Swagger UI) |

---

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 22+
- Redis 7+
- PostgreSQL 16+ (or use SQLite for local dev)

### Development Setup

```bash
# Clone
git clone https://github.com/packetloss404/docvault.git
cd docvault

# Backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r docvault/requirements/dev.txt
cp .env.example docvault/.env
cd docvault
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 5000

# Frontend (separate terminal)
cd src-ui
npm install
npx ng serve
```

Open **http://localhost:4200** and log in. The API runs on port 5000.

### Docker Compose

```bash
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

This starts all services: Django on port 8000, Celery worker, PostgreSQL, Redis, and MinIO.

---

## Configuration

All configuration is via environment variables. See [`.env.example`](.env.example) for the full list with descriptions.

### Key Variables

| Variable | Default | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | — | **Required.** Change in production |
| `DATABASE_URL` | `sqlite:///db.sqlite3` | PostgreSQL or SQLite connection string |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string |
| `STORAGE_BACKEND` | `local` | `local` or `s3` |
| `LLM_ENABLED` | `false` | Enable AI features |
| `LLM_PROVIDER` | `openai` | `openai`, `azure`, or `ollama` |
| `ELASTICSEARCH_ENABLED` | `false` | Enable Elasticsearch |
| `OIDC_SERVER_URL` | — | OIDC provider URL for SSO |
| `STORAGE_ENCRYPTION_ENABLED` | `false` | Enable AES encryption at rest |

---

## API

Interactive API documentation is available at `/api/docs/` (Swagger UI) when the server is running.

All endpoints are under `/api/v1/`:

| Endpoint | Description |
|---|---|
| `/api/v1/auth/` | Login, register, profile, 2FA |
| `/api/v1/documents/` | Document CRUD, upload, versions, barcode labels, bulk export |
| `/api/v1/tags/`, `/correspondents/`, `/cabinets/` | Organization |
| `/api/v1/search/` | Full-text search, autocomplete, analytics, click tracking |
| `/api/v1/ai/` | Semantic search, chat, summarize, entities, suggest title |
| `/api/v1/workflow-templates/` | Workflow management |
| `/api/v1/signature-requests/` | E-signature workflows |
| `/api/v1/esignatures/verify/` | External signer verification |
| `/api/v1/legal-holds/` | Document preservation |
| `/api/v1/storage/` | Dedup stats, integrity verification |
| `/api/v1/security/users/`, `/groups/`, `/roles/` | RBAC admin |
| `/api/v1/portals/` | Contributor portal management |
| `/api/v1/sources/`, `/mail-accounts/` | Document ingestion sources |
| `/api/v1/zone-ocr-templates/` | Zone OCR configuration |
| `/api/v1/entities/` | Named entity recognition |
| `/api/v1/relationships/` | Document relationships and graph |
| `/health/`, `/ready/`, `/metrics/` | Observability |

---

## Testing

```bash
# Backend — 1,029 tests
cd docvault
python manage.py test

# Frontend — 525 tests
cd src-ui
npx ng test

# Total: 1,554 tests
```

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

The Helm chart deploys: web (Gunicorn), worker (Celery), beat (scheduler), PostgreSQL, Redis, and a PVC for media storage. Ingress is configurable.

---

## Project Structure

```
docvault/
├── docvault/             # Django project root (manage.py, settings, urls)
│   ├── ai/               # LLM integration (chat, embeddings, semantic search)
│   ├── annotations/      # Visual document annotations
│   ├── collaboration/    # Comments, checkout, share links
│   ├── core/             # Base models, health checks, bulk operations
│   ├── documents/        # Core document models, views, signals
│   ├── entities/         # Named entity recognition
│   ├── esignatures/      # E-signature workflows
│   ├── legal_hold/       # Legal hold for compliance
│   ├── ml/               # ML classification pipeline
│   ├── notifications/    # WebSocket notifications, quotas
│   ├── organization/     # Tags, cabinets, correspondents, custom fields
│   ├── physical_records/ # Physical document tracking
│   ├── portal/           # Public contributor portal
│   ├── processing/       # OCR, barcode detection, pipeline
│   ├── relationships/    # Document relationships and graph
│   ├── search/           # Full-text search, saved views, analytics
│   ├── security/         # Auth, audit logging, GPG, 2FA, OIDC
│   ├── sources/          # Email, watch folder, S3 ingestion
│   ├── storage/          # Storage backends, CAS, deduplication
│   ├── workflows/        # State machine workflows
│   └── zone_ocr/         # Template-based field extraction
├── src-ui/               # Angular 21 frontend
│   └── src/app/
│       ├── components/   # 68+ UI components
│       ├── services/     # 23 API services
│       ├── guards/       # Auth + admin route guards
│       └── models/       # TypeScript interfaces
├── deploy/               # Helm charts, Kubernetes manifests
├── dev/                  # Sprint plans, checklists, feature specs
└── docs/                 # Project documentation
```

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, code style guidelines, and PR process.

- [Report a bug](.github/ISSUE_TEMPLATE/bug_report.md)
- [Request a feature](.github/ISSUE_TEMPLATE/feature_request.md)
- [Security vulnerabilities](SECURITY.md) — please report privately

---

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).

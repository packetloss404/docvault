# Sprint 18: UI Polish, Deployment & Documentation

## Phase: 6 - Collaboration & Polish
## Duration: 2 weeks
## Prerequisites: Sprint 17 (Security Hardening & Enterprise Features)

---

## Sprint Goal
Final sprint: polish the UI (dashboard widgets, dark mode, i18n), build deployment tooling (Kubernetes Helm chart, production Docker optimization), add monitoring/observability, and write comprehensive documentation.

---

## Context for Agents

### Read Before Starting
- `/doc/product-spec.md` - Section 4 (UI/UX) and Section 5 (Non-Functional Requirements)
- `/doc/architecture.md` - Section 8 (Deployment) and Section 9 (Monitoring)
- All sprint documents for feature completeness verification

---

## Tasks

### Task 18.1: Dashboard Polish
- Drag-and-drop widget layout (using CDK drag-drop)
- Widget types: Welcome, Statistics, Recent Documents, Saved Views, Upload, Activity Feed, Workflow Queue, Processing Status
- Per-user dashboard persistence (save widget positions in user preferences)
- Responsive grid layout (2-column on desktop, 1-column on mobile)
- Statistics widget: document counts by type, recent uploads, storage usage

### Task 18.2: Dark Mode & Theming
- CSS custom properties for theme colors
- Theme toggle in user menu (light/dark/system)
- Theme preference saved per user
- Bootstrap dark mode support
- Custom color scheme support (admin-configurable primary/accent colors)
- Logo customization (upload custom logo via admin)

### Task 18.3: Multi-Language Support (i18n)
- Angular i18n setup with @angular/localize
- Extract all UI strings to message files
- Initial translations: English, German, French, Spanish
- Language selector in user settings
- Server-side language detection (Accept-Language header)
- Date/number formatting per locale

### Task 18.4: Workflow Designer UI
- Visual state machine builder (canvas-based or SVG)
- Drag-and-drop state placement
- Click-to-connect transitions between states
- Property panels for states, transitions, actions
- Condition editor with syntax highlighting
- Workflow template preview (read-only visualization)
- Test/simulation mode (step through workflow without affecting documents)

### Task 18.5: Bulk Operations UI
- Multi-select checkbox on document list
- Bulk action toolbar: add tags, set correspondent, set type, delete, download
- Bulk download (ZIP generation with progress)
- Select all / select page / deselect all
- Confirmation dialogs for destructive operations
- Progress tracking for bulk operations

### Task 18.6: Production Docker Image
- Multi-stage Docker build optimization:
  - Stage 1: Angular build (Node 22)
  - Stage 2: Python dependencies (pip/uv)
  - Stage 3: Final image (Python 3.13-slim + system deps)
- s6-overlay init system for process management
- Health check configuration
- Non-root user execution
- Volume mounts: /data, /media, /consume, /export
- Environment variable documentation
- Image size optimization (< 1GB target)

### Task 18.7: Kubernetes Helm Chart
- Helm chart in `deploy/helm/docvault/`:
  - Deployment for web server (with HPA)
  - Deployment for Celery worker (with HPA)
  - Deployment for Celery beat (single replica)
  - StatefulSet for PostgreSQL (or external DB option)
  - StatefulSet for Redis (or external Redis option)
  - StatefulSet for Elasticsearch (or external ES option)
  - Service, Ingress, ConfigMap, Secret resources
  - PersistentVolumeClaim for media storage
- values.yaml with comprehensive defaults
- NOTES.txt with post-install instructions

### Task 18.8: Monitoring & Observability
- Health check endpoint: GET `/health/` (DB, Redis, Elasticsearch status)
- Readiness check: GET `/ready/` (all services connected)
- Prometheus metrics endpoint: GET `/metrics/`
- Key metrics: request count/latency, document processing rate, OCR time, task queue depth, active users, storage usage, error rates
- Structured JSON logging (all services)
- Correlation IDs for request tracing
- Sentry integration (optional, via `SENTRY_DSN` env var)

### Task 18.9: Documentation
- **README.md**: Project overview, quick start, features, screenshots
- **docs/getting-started.md**: Installation guide (Docker, manual, Kubernetes)
- **docs/configuration.md**: All environment variables, settings reference
- **docs/api-reference.md**: Link to OpenAPI docs, authentication guide, examples
- **docs/administration.md**: User management, sources, workflows, retention
- **docs/plugin-development.md**: How to create custom processing plugins
- **docs/contributing.md**: Development setup, testing, PR guidelines
- **docs/migration.md**: How to migrate from Paperless-ngx or Mayan EDMS
- **CHANGELOG.md**: Version history
- **LICENSE**: Open source license (GPL v3 or Apache 2.0)

### Task 18.10: Performance Testing & Final QA
- Load testing with sample document corpus (1000+ documents)
- Search performance benchmarks (< 500ms for typical queries)
- Upload throughput testing (concurrent uploads)
- OCR processing benchmark
- Memory usage profiling
- Database query optimization (N+1 query detection)
- Frontend bundle size analysis
- Lighthouse audit for frontend performance
- Security checklist verification (OWASP Top 10)
- Cross-browser testing (Chrome, Firefox, Safari, Edge)

---

## Definition of Done (Sprint 18 + Entire Project)
- [ ] Dashboard with drag-and-drop widgets works
- [ ] Dark mode toggle works
- [ ] At least 4 languages supported
- [ ] Workflow designer allows visual workflow creation
- [ ] Bulk operations (tag, delete, download) work
- [ ] Production Docker image builds and runs
- [ ] Kubernetes Helm chart deploys successfully
- [ ] Health/readiness endpoints work
- [ ] Prometheus metrics available
- [ ] Structured logging configured
- [ ] README and all documentation written
- [ ] Performance meets targets (< 500ms search, < 2s upload)
- [ ] Security checklist passes
- [ ] All tests pass across all modules
- [ ] End-to-end smoke test passes:
  1. User registers and logs in
  2. Uploads a PDF document
  3. Document is OCR'd and indexed
  4. ML classifier suggests tags
  5. User searches and finds document
  6. User creates a workflow and applies it
  7. User shares document via link
  8. Guest accesses shared document

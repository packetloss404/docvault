# Sprint 6: Thumbnails, Versions & Non-Destructive Mode

## Phase: 2 - Document Processing
## Duration: 2 weeks
## Prerequisites: Sprint 5 (Parsers & OCR)

---

## Sprint Goal
Implement thumbnail generation, document versioning with full history, non-destructive storage mode, archive file management, pre/post-consume hooks, and the frontend document detail page with preview, metadata, and content tabs.

---

## Context for Agents

### Read Before Starting
- `/doc/product-spec.md` - Section 2.3 (Processing Module) and 2.8 (Storage Module)
- `/doc/research/lodestone-analysis.md` - Non-destructive processing philosophy
- `/doc/research/mayan-edms-analysis.md` - Document versioning model

---

## Tasks

### Task 6.1: Thumbnail Generation Plugin
- ThumbnailPlugin (order 130) generates WebP previews from first page
- Uses pdf2image for PDFs, Pillow for images
- Configurable thumbnail size (default 400x560)
- Store in thumbnails directory with document ID naming
- Thumbnail endpoint: GET `/api/v1/documents/{id}/preview/`
- Cache headers for browser caching (ETag-based)

### Task 6.2: Document Version Management
- DocumentVersion model (already created in Sprint 1) - implement business logic
- Version creation on re-upload (POST `/api/v1/documents/{id}/files/`)
- Version listing API (GET `/api/v1/documents/{id}/versions/`)
- Active version switching (POST `/api/v1/documents/{id}/versions/{vid}/activate/`)
- Version comparison endpoint (diff between two versions' content)
- Auto-increment version numbers
- Version comments for change tracking

### Task 6.3: Non-Destructive Storage Mode
- Configuration: `NON_DESTRUCTIVE_MODE=true` (default: true)
- When enabled: originals stored separately, never modified
- Archive (searchable PDF) stored alongside original
- Storage path template support (Jinja2-based, from Paperless-ngx StoragePath)
- File integrity verification (checksum on read)
- Document download endpoint with option for original or archive
  - GET `/api/v1/documents/{id}/download/?version=original`
  - GET `/api/v1/documents/{id}/download/?version=archive`

### Task 6.4: Pre/Post-Consume Hook Plugin
- PreConsumeHookPlugin (order 40): Execute user-supplied script before processing
- PostConsumeHookPlugin (order 140): Execute after all processing complete
- Scripts receive document info as environment variables
- Configurable via `PRE_CONSUME_SCRIPT` and `POST_CONSUME_SCRIPT` env vars
- Timeout handling (default 30 seconds)
- Error handling (script failure doesn't block processing, logged as warning)

### Task 6.5: Document Detail Frontend Page
- Document detail component with tabbed interface
- **Details tab**: Title, document type, correspondent, tags, dates, ASN, metadata
- **Content tab**: Extracted text display with search highlighting
- **Preview tab**: PDF viewer (PDF.js) with zoom, rotation, page navigation
- **Metadata tab**: File info (MIME type, size, checksum, original filename)
- Edit mode for title, document type, correspondent, tags
- Save/cancel buttons
- Breadcrumb navigation

### Task 6.6: Frontend Document List Page
- Document list component connected to API
- Table view with configurable columns
- Pagination controls
- Sort by column click
- Basic text search input
- Document type filter dropdown
- Click row to navigate to detail page

---

## Definition of Done
- [ ] Thumbnails generated for all document types (WebP format)
- [ ] Preview endpoint serves thumbnails with caching
- [ ] Document versioning works (upload new version, list, activate)
- [ ] Non-destructive mode preserves originals
- [ ] Download endpoint supports original and archive versions
- [ ] Pre/post-consume scripts execute when configured
- [ ] Frontend document detail page with 4 tabs works
- [ ] Frontend document list page with sorting, filtering, pagination works
- [ ] PDF.js viewer renders PDF previews in browser
- [ ] All new features have unit tests

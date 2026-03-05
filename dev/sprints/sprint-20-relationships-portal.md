# Sprint 20: Document Relationships & Contributor Portal

## Phase: 7 - Advanced Features
## Duration: 2 weeks
## Prerequisites: Sprint 18 (UI Polish, Deployment & Documentation)

---

## Sprint Goal
Implement typed document relationships with graph visualization (knowledge graph), and build a contributor portal for external document collection including guest uploads, document requests with deadlines, and branded portal pages.

---

## Context for Agents

### Read Before Starting
- `/doc/product-spec.md` - Section 2.2 (Organization Module - Document Relationships), Section 2.10 (Collaboration Module - Contributor Portal)
- `/doc/research/extended-market-analysis.md` - Features #3 (Document Request Portal), #5 (Knowledge Graph)
- `/doc/sprints/sprint-07-tags-cabinets.md` - Existing organization models
- `/doc/sprints/sprint-16-collaboration.md` - Existing share link system
- `/doc/sprints/sprint-08-custom-fields.md` - Custom field system (used by portal metadata forms)

---

## Tasks

### Task 20.1: Document Relationship Models & API
- Add to `organization/` app (or create `relationships/` app)
- RelationshipType model:
  - `name` (CharField, unique - e.g., "supersedes", "references")
  - `label` (CharField - display name, e.g., "Supersedes")
  - `inverse_label` (CharField - display name for reverse direction, e.g., "Superseded by")
  - `bidirectional` (BooleanField - if True, relationship applies both ways equally)
  - `is_builtin` (BooleanField - protect system types from deletion)
  - `color` (CharField - hex color for graph edges)
  - `icon` (CharField - icon name)
- Built-in relationship types (seeded via data migration):
  - `supersedes` / `is-superseded-by` (directional, auto-marks target as obsolete)
  - `references` / `is-referenced-by` (directional)
  - `is-attachment-of` / `has-attachment` (directional)
  - `responds-to` / `has-response` (directional)
  - `contradicts` (bidirectional)
  - `relates-to` (bidirectional)
  - `amends` / `is-amended-by` (directional)
  - `duplicates` (bidirectional)
- DocumentRelationship model:
  - `source_document` (FK to Document)
  - `target_document` (FK to Document)
  - `relationship_type` (FK to RelationshipType)
  - `notes` (TextField, optional)
  - `created_by` (FK to User)
  - `created_at` (DateTimeField, auto_now_add)
  - Unique constraint on (source_document, target_document, relationship_type)
  - For bidirectional types, enforce that only one direction is stored (source.id < target.id)
- Supersession chain logic:
  - When creating a "supersedes" relationship:
    - Mark target document with `is_obsolete=True` flag
    - Optionally cascade: if target already superseded something, mark that as obsolete too
  - Add `is_obsolete` BooleanField to Document model (default=False)
  - Filter obsolete documents out of default search results (configurable)
- API:
  - GET `/api/v1/documents/{id}/relationships/` - List all relationships for a document
    - Returns both outgoing (source=this doc) and incoming (target=this doc) relationships
    - Include relationship type label (using inverse_label for incoming)
  - POST `/api/v1/documents/{id}/relationships/` - Create relationship
    - Body: `{ "target_document": id, "relationship_type": id, "notes": "" }`
  - DELETE `/api/v1/documents/{id}/relationships/{rid}/` - Remove relationship
  - GET `/api/v1/relationship_types/` - List relationship types
  - POST `/api/v1/relationship_types/` - Create custom relationship type (admin)
  - GET `/api/v1/documents/{id}/relationship_graph/` - Graph data for visualization
    - Returns nodes (documents) and edges (relationships) up to N hops (default 2)
    - Include document title, type, tags for node rendering

### Task 20.2: Relationship Frontend - Panel & Graph
- **Relationship panel** on document detail page:
  - "Relationships" tab showing all linked documents
  - Grouped by relationship type
  - Each entry shows: document title, relationship label, date linked, link to document
  - "Add relationship" button:
    - Document picker (search/typeahead)
    - Relationship type dropdown
    - Optional notes
  - "Remove relationship" with confirmation
  - Supersession chain indicator (show chain: A supersedes B supersedes C)
- **Graph visualization** (expandable panel or full-page view):
  - Use D3.js force-directed graph or vis.js network
  - Nodes = documents (labeled with title, colored by document type)
  - Edges = relationships (colored by type, labeled with type name)
  - Current document highlighted as center node
  - Click node to navigate to that document
  - Hover for tooltip (document metadata summary)
  - Zoom, pan, drag nodes
  - Legend showing relationship type colors
  - Depth control slider (1-3 hops)
- **Document list integration**:
  - "Has relationships" filter
  - Relationship count column (optional)
  - "Is obsolete" filter

### Task 20.3: Contributor Portal Models & API
- Create `portal/` app
- PortalConfig model:
  - `name` (CharField - e.g., "Client Document Portal")
  - `slug` (SlugField, unique - URL-safe identifier)
  - `description` (TextField)
  - `welcome_text` (TextField - displayed on portal page, supports markdown)
  - `logo` (ImageField, optional - custom portal branding)
  - `primary_color` (CharField, optional - hex color override)
  - `owner` (FK to User - portal administrator)
  - `is_active` (BooleanField, default=True)
  - `require_email` (BooleanField, default=True - collect uploader's email)
  - `required_fields` (M2M to CustomField - fields uploader must fill)
  - `default_document_type` (FK to DocumentType, optional)
  - `default_tags` (M2M to Tag - auto-applied to uploaded documents)
  - `target_cabinet` (FK to Cabinet, optional - where uploads are filed)
  - `max_file_size_mb` (IntegerField, default=50)
  - `allowed_mime_types` (ArrayField, optional - restrict file types)
  - `created_at`, `updated_at`
- DocumentRequest model:
  - `portal` (FK to PortalConfig, optional)
  - `title` (CharField - what document is being requested)
  - `description` (TextField - detailed instructions for the submitter)
  - `created_by` (FK to User)
  - `assignee_name` (CharField - who should submit the document)
  - `assignee_email` (EmailField - where to send the request)
  - `deadline` (DateTimeField, optional)
  - `token` (UUIDField, unique - used in the request URL)
  - `status` (CharField choices: PENDING, PARTIALLY_FULFILLED, FULFILLED, EXPIRED, CANCELLED)
  - `reminder_sent_count` (IntegerField, default=0)
  - `last_reminder_sent` (DateTimeField, nullable)
  - `created_at`, `updated_at`
- PortalSubmission model:
  - `portal` (FK to PortalConfig, optional)
  - `request` (FK to DocumentRequest, optional)
  - `document` (FK to Document, nullable - set after review/approval)
  - `uploaded_file` (FileField - stored in staging area before review)
  - `submitter_name` (CharField)
  - `submitter_email` (EmailField)
  - `metadata_values` (JSONField - values for required custom fields)
  - `status` (CharField choices: PENDING_REVIEW, APPROVED, REJECTED)
  - `reviewed_by` (FK to User, nullable)
  - `reviewed_at` (DateTimeField, nullable)
  - `rejection_reason` (TextField, nullable)
  - `submitted_at` (DateTimeField, auto_now_add)
  - `ip_address` (GenericIPAddressField)

### Task 20.4: Contributor Portal Public Endpoints
- Public portal page: GET `/api/v1/portal/{slug}/`
  - Returns portal config (name, description, welcome_text, logo, required_fields schema)
  - No authentication required
  - 404 if portal inactive
- Guest upload: POST `/api/v1/portal/{slug}/upload/`
  - No authentication required
  - Multipart form: file + submitter_name + submitter_email + metadata_values (JSON)
  - Validate: file size, MIME type, required fields
  - Create PortalSubmission with status=PENDING_REVIEW
  - Send confirmation email to submitter
  - Send notification to portal owner
  - Rate limiting: max 10 uploads per IP per hour
- Document request page: GET `/api/v1/request/{token}/`
  - Returns request details (title, description, deadline, portal branding)
  - No authentication required
  - 404 if expired or cancelled
- Request upload: POST `/api/v1/request/{token}/upload/`
  - Same as portal upload but linked to specific request
  - Update request status to PARTIALLY_FULFILLED or FULFILLED
- Celery tasks:
  - `send_request_email`: Send document request email with tokenized link
  - `send_deadline_reminder`: Remind assignees of approaching deadlines (1 day, 3 days before)
  - `expire_requests`: Auto-expire past-deadline unfulfilled requests
  - Beat schedule: check reminders daily at 9 AM

### Task 20.5: Contributor Portal Admin & Review Queue
- API (authenticated):
  - GET/POST `/api/v1/portals/` - Portal CRUD (admin/staff)
  - GET/PATCH/DELETE `/api/v1/portals/{id}/`
  - GET/POST `/api/v1/document_requests/` - Request CRUD
  - GET/PATCH/DELETE `/api/v1/document_requests/{id}/`
  - POST `/api/v1/document_requests/{id}/send/` - Send request email
  - POST `/api/v1/document_requests/{id}/remind/` - Send reminder
  - GET `/api/v1/portal_submissions/` - List submissions (filterable by status, portal, date)
  - POST `/api/v1/portal_submissions/{id}/approve/` - Approve and ingest into document archive
  - POST `/api/v1/portal_submissions/{id}/reject/` - Reject with reason (sends email to submitter)
- Approval workflow:
  1. Admin reviews submission (preview file, check metadata)
  2. On approve: create Document from uploaded file, apply portal defaults (type, tags, cabinet)
  3. Run standard processing pipeline on new document
  4. Link Document to PortalSubmission
  5. Send approval notification to submitter (optional)
  6. On reject: send rejection email with reason, submitter can re-upload

### Task 20.6: Contributor Portal Frontend
- **Portal configuration page** (admin):
  - Create/edit portal: name, slug, description, welcome text (markdown preview)
  - Logo upload with preview
  - Primary color picker
  - Required custom fields selector (checkboxes)
  - Default document type, tags, cabinet selectors
  - File restrictions (max size, allowed types)
  - Portal URL display with copy button
- **Document request management page**:
  - Create request: title, description, assignee name/email, deadline picker
  - Request list with status badges (pending, fulfilled, expired)
  - Send/resend email button
  - Send reminder button
  - Bulk operations (send all reminders)
- **Review queue page**:
  - Filterable list of pending submissions
  - Submission detail: file preview, submitter info, metadata values, timestamps
  - Approve button (with optional document type/tag override)
  - Reject button (with reason text area)
  - Batch approve for trusted portals
- **Public portal page** (Angular route, no auth):
  - Branded header (logo, portal name)
  - Welcome text (rendered markdown)
  - Upload form: file drop zone, name, email, custom fields
  - Progress bar during upload
  - Success/error messages
  - Clean, professional design suitable for external users
- **Public request page** (Angular route, no auth):
  - Request details (title, description, deadline)
  - Upload form (same as portal but pre-linked to request)
  - Deadline countdown indicator

---

## Dependencies

### New Python Packages
```
# No new packages - uses existing Django, DRF, Celery infrastructure
# D3.js or vis.js added via npm for graph visualization
```

### New npm Packages
```
d3@^7 or vis-network@^9  (for relationship graph visualization)
```

---

## Definition of Done
- [ ] Relationship types can be created (built-in + custom)
- [ ] Documents can be linked with typed relationships
- [ ] Relationship panel shows all links on document detail
- [ ] Graph visualization renders interactive network view
- [ ] Supersession chain marks target documents as obsolete
- [ ] Contributor portal can be configured with branding
- [ ] External users can upload documents via portal (no auth)
- [ ] Document requests can be sent via email with tokenized links
- [ ] Deadline reminders are sent automatically
- [ ] Submissions land in review queue for admin approval
- [ ] Approved submissions are ingested into document archive
- [ ] All features have unit tests
- [ ] Public endpoints are rate-limited and validated

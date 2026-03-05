# Sprint 16: Collaboration Features

## Phase: 6 - Collaboration & Polish
## Duration: 2 weeks
## Prerequisites: Sprint 15 (LLM Integration & Vector Search)

---

## Sprint Goal
Build multi-user collaboration features: document comments/notes, check-in/check-out locking, share links with guest access, activity feeds, and the corresponding frontend components.

---

## Context for Agents

### Read Before Starting
- `/doc/product-spec.md` - Section 2.10 (Collaboration Module)
- `/doc/research/mayan-edms-analysis.md` - Section 7 (Check-in/Check-out)
- `/doc/research/paperless-ngx-analysis.md` - Section 13 (Notes), Section 14 (Share Links)

---

## Tasks

### Task 16.1: Comments/Notes System
- Create `collaboration/` app
- Comment model: document (FK), user (FK), text (TextField, markdown support), created_at, updated_at
- Soft delete on comments
- Full-text indexing of notes in Elasticsearch
- Comment CRUD API nested under documents:
  - GET/POST `/api/v1/documents/{id}/comments/`
  - PATCH/DELETE `/api/v1/documents/{id}/comments/{cid}/`
- Notification trigger on comment creation

### Task 16.2: Check-in/Check-out
- Checkout model: document (OneToOne), user (FK), checked_out_at, expiration, block_new_uploads (bool)
- Only one checkout per document (enforced by OneToOne)
- Auto-release after expiration (Celery task, runs every 5 minutes)
- Forced check-in by document owner or admin
- API:
  - POST `/api/v1/documents/{id}/checkout/` (lock)
  - POST `/api/v1/documents/{id}/checkin/` (unlock)
  - GET `/api/v1/documents/{id}/checkout_status/`
- Block uploads/edits while checked out (except by checker-outer)

### Task 16.3: Share Links
- ShareLink model: document (FK), slug (unique), created_by (FK), expiration (optional), password_hash (optional), file_version (ORIGINAL/ARCHIVE), download_count (int)
- ShareLinkBundle model: slug, documents (M2M), created_by, expiration, status (PENDING/PROCESSING/READY), file_path, size_bytes
- Public access endpoint: GET `/api/v1/share/{slug}/` (no auth required)
- Password verification for protected links
- Download tracking (increment counter on access)
- Expiration enforcement (404 after expiration)
- Bundle ZIP generation (Celery task)
- API:
  - POST `/api/v1/documents/{id}/share/` (create share link)
  - GET `/api/v1/share_links/` (list my share links)
  - DELETE `/api/v1/share_links/{id}/` (revoke)

### Task 16.4: Activity Feed
- Leverage audit/event system from Security module
- Per-document activity timeline: uploads, edits, comments, shares, workflow transitions, downloads
- Recent activity API: GET `/api/v1/documents/{id}/activity/`
- Global activity feed: GET `/api/v1/activity/` (filtered by permission)
- Dashboard widget for recent activity

### Task 16.5: Frontend Collaboration Components
- **Notes tab** in document detail: list comments, add new, edit, delete
- **Markdown rendering** for comments (ngx-markdown or similar)
- **Check-out indicator**: lock icon on document list and detail
- **Check-out/Check-in buttons** in document detail toolbar
- **Share dialog**: generate link, set expiration, set password, copy to clipboard
- **Share link management page**: list all share links with revoke option
- **Activity timeline**: chronological feed on document detail page
- **Dashboard widget**: recent activity across all documents

---

## Definition of Done
- [ ] Comments CRUD works with markdown support
- [ ] Comments indexed in Elasticsearch for search
- [ ] Check-in/check-out locks documents
- [ ] Auto-release after expiration works
- [ ] Share links provide guest access to documents
- [ ] Password-protected share links work
- [ ] Share link expiration enforced
- [ ] Bundle download generates ZIP of multiple documents
- [ ] Activity feed shows per-document history
- [ ] Frontend notes tab, lock indicator, share dialog, activity timeline work
- [ ] All features have unit tests

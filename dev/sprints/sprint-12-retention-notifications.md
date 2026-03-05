# Sprint 12: Retention, Quotas & Notifications

## Phase: 4 - Workflow & Automation
## Duration: 2 weeks
## Prerequisites: Sprint 11 (Trigger-Action Rules & Sources)

---

## Sprint Goal
Implement document retention policies (auto-trash/delete), usage quotas, and the notification system (in-app via WebSocket, email, webhooks).

---

## Context for Agents

### Read Before Starting
- `/doc/product-spec.md` - Section 2.5 (Retention Policies), 2.6 (Quotas), 2.11 (Notifications)
- `/doc/research/mayan-edms-analysis.md` - Retention policies (DocumentType model)

---

## Tasks

### Task 12.1: Retention Policy Enforcement
- Retention fields already on DocumentType (from Sprint 1): trash_time_period/unit, delete_time_period/unit
- Celery task `enforce_retention` (runs daily at 2 AM):
  - Find documents past trash deadline -> soft_delete()
  - Find trashed documents past delete deadline -> hard delete (files + DB)
- Stub pruning: delete incomplete uploads after configurable expiration
- Admin UI for setting retention policies on document types
- Retention policy dry-run mode (log what would be deleted)

### Task 12.2: Usage Quotas
- Quota model: user (FK or null for global), group (FK or null), max_documents (int or null), max_storage_bytes (bigint or null)
- Quota enforcement middleware/check on upload:
  - Count user's documents, compare to quota
  - Sum user's file sizes, compare to storage quota
  - Return 429 if quota exceeded
- Quota API: GET `/api/v1/quotas/usage/` (current usage vs limits)
- Admin-only quota CRUD API

### Task 12.3: Notification System
- Notification model: user (FK), event_type, title, body, document (FK, optional), read (bool), created_at
- NotificationPreference model: user (FK), event_type, channel (in_app/email/webhook), enabled
- Channels:
  - In-app: create Notification record, push via WebSocket
  - Email: send via Django email backend with templates
  - Webhook: POST to configured URL
- Event types: document_added, document_processed, processing_failed, workflow_transition, comment_added, share_accessed, retention_warning

### Task 12.4: Notification API & Frontend
- GET `/api/v1/notifications/` (unread, paginated)
- POST `/api/v1/notifications/{id}/read/` (mark as read)
- POST `/api/v1/notifications/read_all/` (mark all as read)
- GET `/api/v1/notifications/preferences/` (user preferences)
- PATCH `/api/v1/notifications/preferences/` (update preferences)
- Frontend: notification bell icon with unread count
- Frontend: notification dropdown/panel
- Frontend: notification preferences page

---

## Definition of Done
- [ ] Retention policies auto-trash and auto-delete documents on schedule
- [ ] Stub pruning cleans up incomplete uploads
- [ ] Usage quotas enforce document count and storage limits
- [ ] Quota exceeded returns 429 on upload
- [ ] In-app notifications delivered via WebSocket
- [ ] Email notifications sent for configured events
- [ ] Webhook notifications delivered
- [ ] Notification API works (list, read, preferences)
- [ ] Frontend notification bell and panel work
- [ ] All features have unit tests

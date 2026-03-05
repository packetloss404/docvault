# Sprint 21: E-Signatures & Visual Annotations

## Phase: 7 - Advanced Features
## Duration: 2 weeks
## Prerequisites: Sprint 18 (UI Polish, Deployment & Documentation)

---

## Sprint Goal
Implement e-signature workflow with external signer support (no account required) and visual page-level annotations. E-signatures enable legally binding digital signing flows. Annotations provide a non-destructive overlay for highlighting, commenting, and marking up document pages.

---

## Context for Agents

### Read Before Starting
- `/doc/product-spec.md` - Section 2.6 (Security Module - E-Signatures), Section 2.10 (Collaboration Module - Visual Annotations)
- `/doc/research/extended-market-analysis.md` - Features #1 (E-Signature), #6 (Visual Annotations)
- `/doc/sprints/sprint-16-collaboration.md` - Existing share link system (similar tokenized URL pattern)
- `/doc/sprints/sprint-17-security-enterprise.md` - Existing GPG signing (complementary, not replacement)
- `/doc/sprints/sprint-06-thumbnails-versions.md` - Document versioning system

---

## Tasks

### Task 21.1: E-Signature Models
- Create `esignatures/` app
- SignatureRequest model:
  - `document` (FK to Document)
  - `title` (CharField - request title/subject)
  - `message` (TextField, optional - message to signers)
  - `created_by` (FK to User)
  - `status` (CharField choices: DRAFT, SENT, IN_PROGRESS, COMPLETED, CANCELLED, EXPIRED)
  - `signing_order` (CharField choices: SEQUENTIAL, PARALLEL)
  - `expiration` (DateTimeField, optional)
  - `completed_at` (DateTimeField, nullable)
  - `certificate_pdf` (FileField, nullable - certificate of completion)
  - `created_at`, `updated_at`
- SignatureField model:
  - `request` (FK to SignatureRequest)
  - `signer` (FK to Signer)
  - `page` (IntegerField - 1-indexed page number)
  - `x` (FloatField - percentage from left, 0.0-1.0)
  - `y` (FloatField - percentage from top, 0.0-1.0)
  - `width` (FloatField - percentage of page width)
  - `height` (FloatField - percentage of page height)
  - `field_type` (CharField choices: SIGNATURE, INITIALS, DATE, TEXT, CHECKBOX)
  - `required` (BooleanField, default=True)
  - `order` (IntegerField - field completion order within signer)
  - `value` (TextField, nullable - filled value after signing)
  - `signed_at` (DateTimeField, nullable)
- Signer model:
  - `request` (FK to SignatureRequest)
  - `name` (CharField)
  - `email` (EmailField)
  - `role` (CharField - e.g., "Buyer", "Seller", "Witness")
  - `order` (IntegerField - signing sequence order)
  - `token` (UUIDField, unique - used in the signing URL)
  - `status` (CharField choices: PENDING, VIEWED, SIGNED, DECLINED)
  - `signed_at` (DateTimeField, nullable)
  - `ip_address` (GenericIPAddressField, nullable)
  - `user_agent` (TextField, nullable)
  - `verification_method` (CharField choices: EMAIL, SMS, NONE)
  - `verification_code` (CharField, nullable - OTP for SMS verification)
  - `viewed_pages` (JSONField, default=[] - list of page numbers viewed)
- SignatureAuditEvent model:
  - `request` (FK to SignatureRequest)
  - `signer` (FK to Signer, nullable)
  - `event_type` (CharField: CREATED, SENT, VIEWED, PAGE_VIEWED, SIGNED, DECLINED, COMPLETED, CANCELLED, EXPIRED, REMINDER_SENT)
  - `detail` (JSONField - event-specific data, e.g., page number for PAGE_VIEWED)
  - `ip_address` (GenericIPAddressField, nullable)
  - `timestamp` (DateTimeField, auto_now_add)

### Task 21.2: E-Signature Workflow Engine
- Signature request lifecycle:
  1. **Create**: User places signature fields on document pages, adds signers
  2. **Send**: System emails each signer their tokenized link
  3. **View**: Signer opens document, views pages (tracked)
  4. **Sign**: Signer fills signature fields, submits
  5. **Complete**: All signers done, certificate generated
- Sequential signing:
  - Only send email to current signer (lowest order among unsigned)
  - When current signer completes, auto-send to next
  - Skip declined signers (mark request as declined if all decline)
- Parallel signing:
  - Send all emails simultaneously
  - Track completion independently
- Signature capture:
  - Type name (rendered as script font)
  - Draw signature (canvas freehand drawing)
  - Upload signature image
  - Store as PNG with transparent background
- Identity verification:
  - Email verification: link sent to signer's email (implicit)
  - SMS verification: send OTP via SMS, signer enters code before signing
  - IP logging: record signer's IP on every action
- Certificate of completion:
  - Generated PDF containing:
    - Original document with signature images overlaid
    - Audit trail (all events with timestamps, IPs)
    - SHA-256 hash of original document
    - Signer details (name, email, IP, signing timestamp)
  - Stored as new document version or separate file
- Celery tasks:
  - `send_signature_email`: Send signing invitation
  - `send_signature_reminder`: Remind pending signers (configurable: 3 days, 7 days)
  - `expire_signature_requests`: Auto-expire past-deadline requests
  - `generate_completion_certificate`: Build certificate PDF after all sign

### Task 21.3: E-Signature Public Endpoints
- GET `/api/v1/sign/{token}/` (no auth):
  - Returns: document preview (page images), signature fields for this signer, request details
  - Records VIEWED audit event
  - 404 if token invalid, expired, or already signed
- POST `/api/v1/sign/{token}/view_page/` (no auth):
  - Body: `{ "page": 1 }`
  - Records PAGE_VIEWED audit event
  - Required: signer must view all pages before signing (configurable)
- POST `/api/v1/sign/{token}/verify/` (no auth):
  - Body: `{ "code": "123456" }`
  - Verify SMS OTP code (if SMS verification required)
  - Returns verification status
- POST `/api/v1/sign/{token}/complete/` (no auth):
  - Body: `{ "fields": [{ "field_id": 1, "value": "base64_signature_image" }, ...] }`
  - Validate all required fields filled
  - Validate signer has viewed all pages (if required)
  - Store field values, update signer status
  - Record SIGNED audit event
  - Trigger next signer (sequential) or check completion (parallel)
  - Rate limiting: max 5 attempts per token per hour
- POST `/api/v1/sign/{token}/decline/` (no auth):
  - Body: `{ "reason": "..." }`
  - Record DECLINED audit event
  - Notify request creator
- Authenticated endpoints:
  - POST `/api/v1/documents/{id}/signature_request/` - Create new request
  - GET `/api/v1/signature_requests/` - List my requests (created by me)
  - GET `/api/v1/signature_requests/{id}/` - Request detail with audit trail
  - POST `/api/v1/signature_requests/{id}/send/` - Send to signers
  - POST `/api/v1/signature_requests/{id}/cancel/` - Cancel request
  - POST `/api/v1/signature_requests/{id}/remind/` - Send reminders
  - GET `/api/v1/signature_requests/{id}/certificate/` - Download completion certificate

### Task 21.4: E-Signature Frontend
- **Signature field placement** (document detail):
  - "Request Signatures" button in document toolbar
  - Step 1: Add signers (name, email, role, order)
  - Step 2: Place fields on document pages
    - Document page viewer with zoom
    - Drag-and-drop field placement (signature, initials, date, text, checkbox)
    - Color-coded per signer
    - Resize handles on fields
    - Field properties panel (type, required)
  - Step 3: Set options (signing order, expiration, message)
  - Step 4: Review and send
- **Signature request management page**:
  - List all requests with status badges
  - Filter by status, date
  - Detail view with audit trail timeline
  - Send reminders button
  - Cancel button
  - Download certificate button (when completed)
- **Public signing page** (Angular route, no auth):
  - Clean, focused UI (minimal navigation)
  - Document viewer with signature fields highlighted
  - Page navigation with "viewed" checkmarks
  - Signature capture modal:
    - Tab 1: Type name (font preview)
    - Tab 2: Draw signature (canvas with undo/clear)
    - Tab 3: Upload image
  - "Sign & Complete" / "Decline" buttons
  - Verification code input (if SMS verification)
  - Success confirmation page

### Task 21.5: Annotation Models & API
- Create `annotations/` app (or add to `collaboration/` app)
- Annotation model:
  - `document` (FK to Document)
  - `page` (IntegerField - 1-indexed)
  - `annotation_type` (CharField choices: HIGHLIGHT, UNDERLINE, STRIKETHROUGH, STICKY_NOTE, FREEHAND, RECTANGLE, TEXT_BOX, RUBBER_STAMP)
  - `coordinates` (JSONField):
    - For HIGHLIGHT/UNDERLINE/STRIKETHROUGH: `{ "rects": [{ "x": 0.1, "y": 0.2, "width": 0.3, "height": 0.02 }] }`
    - For STICKY_NOTE: `{ "x": 0.5, "y": 0.3 }`
    - For FREEHAND: `{ "points": [{ "x": 0.1, "y": 0.2 }, ...], "stroke_width": 2 }`
    - For RECTANGLE/TEXT_BOX: `{ "x": 0.1, "y": 0.2, "width": 0.3, "height": 0.2 }`
    - For RUBBER_STAMP: `{ "x": 0.5, "y": 0.5, "stamp_type": "APPROVED" }`
    - All coordinates as percentages (0.0-1.0) for resolution independence
  - `content` (TextField, nullable - text content for sticky notes, text boxes, stamps)
  - `color` (CharField, default="#FFFF00" - annotation color)
  - `opacity` (FloatField, default=0.3)
  - `author` (FK to User)
  - `created_at`, `updated_at`
  - `is_private` (BooleanField, default=False - only visible to author)
- AnnotationReply model:
  - `annotation` (FK to Annotation)
  - `author` (FK to User)
  - `text` (TextField)
  - `created_at`
- Rubber stamp types (built-in): APPROVED, REJECTED, DRAFT, CONFIDENTIAL, FINAL, REVIEWED, VOID
- API:
  - GET `/api/v1/documents/{id}/annotations/` - List all annotations (filtered by permission)
    - Query params: `page`, `type`, `author`
  - POST `/api/v1/documents/{id}/annotations/` - Create annotation
  - PATCH `/api/v1/documents/{id}/annotations/{aid}/` - Update annotation
  - DELETE `/api/v1/documents/{id}/annotations/{aid}/` - Delete annotation
  - GET/POST `/api/v1/documents/{id}/annotations/{aid}/replies/` - Replies
  - POST `/api/v1/documents/{id}/annotations/export/` - Export annotated PDF
    - Bake annotations into a copy (reportlab or PyMuPDF overlay)
    - Return as downloadable file (does not modify original)
  - Permission rules:
    - Authors can always edit/delete their own annotations
    - Document owners can delete any annotation
    - Private annotations only visible to author and admins

### Task 21.6: Annotation Frontend
- **Annotation toolbar** on document preview:
  - Tool selection: highlight, underline, strikethrough, sticky note, freehand, rectangle, text box, stamp
  - Color picker
  - Opacity slider
  - Undo/redo
  - Clear all (with confirmation)
  - Toggle annotation visibility (show/hide)
  - Filter by author
  - Toggle private mode
- **Annotation rendering** (overlay on PDF viewer):
  - SVG overlay layer positioned over each page
  - Render each annotation type:
    - HIGHLIGHT: Semi-transparent rectangle
    - UNDERLINE: Line below text
    - STRIKETHROUGH: Line through text
    - STICKY_NOTE: Icon at position, expandable tooltip with content
    - FREEHAND: SVG path from points
    - RECTANGLE: Outlined rectangle
    - TEXT_BOX: Rectangle with text content
    - RUBBER_STAMP: Rotated text stamp image
  - Click annotation to select (show edit/delete options)
  - Drag to move selected annotation
  - Resize handles on rectangles/text boxes
- **Annotation panel** (sidebar):
  - List all annotations for current page
  - Jump to annotation on click
  - Show author, timestamp, type
  - Reply thread (inline)
  - Mark as resolved
- **Export button**: "Download with annotations" (calls export API)
- **W3C Web Annotation compatibility**:
  - Support export/import in W3C Web Annotation JSON-LD format
  - Enables interoperability with other annotation tools

---

## Dependencies

### New Python Packages
```
PyMuPDF>=1.24 (for annotation export/PDF overlay)
reportlab>=4.0 (for certificate of completion generation)
twilio>=9.0 (optional, for SMS verification - configurable)
```

### New npm Packages
```
fabric@^6 or konva@^9 (for canvas-based signature drawing and annotation rendering)
```

---

## Definition of Done
- [ ] Signature requests can be created with field placement on PDF pages
- [ ] External signers receive email with tokenized signing link
- [ ] Signers can view document, place signatures, and complete signing (no account)
- [ ] Sequential and parallel signing orders work
- [ ] Page view tracking ensures signers read before signing
- [ ] Certificate of completion PDF generated after all sign
- [ ] Full audit trail with timestamps and IP addresses
- [ ] Expiration and reminder system works
- [ ] Annotations can be created on document pages (8 types)
- [ ] Annotations rendered as SVG overlay on PDF viewer
- [ ] Annotation replies and threads work
- [ ] Private annotations only visible to author
- [ ] Export annotated PDF bakes annotations into a copy
- [ ] All features have unit tests
- [ ] Public endpoints are rate-limited and validated

# Sprint 22: Legal Hold, Content-Addressable Storage & Physical Records

## Phase: 7 - Advanced Features
## Duration: 2 weeks
## Prerequisites: Sprint 18 (UI Polish, Deployment & Documentation)

---

## Sprint Goal
Implement three enterprise/compliance features: legal hold with custodian management for litigation support, content-addressable storage with binary deduplication for storage efficiency, and physical records management for tracking physical document originals alongside their digital counterparts.

---

## Context for Agents

### Read Before Starting
- `/doc/product-spec.md` - Section 2.6 (Security Module - Legal Hold), Section 2.8 (Storage Module - Content-Addressable), Section 2.12 (Physical Records Module)
- `/doc/research/extended-market-analysis.md` - Features #8 (Content-Addressable), #9 (Legal Hold), #10 (Physical Records)
- `/doc/sprints/sprint-04-storage-upload.md` - Existing storage backend system
- `/doc/sprints/sprint-12-retention-notifications.md` - Existing retention policies (legal hold overrides these)
- `/doc/sprints/sprint-17-security-enterprise.md` - Existing encryption and audit systems

---

## Tasks

### Task 22.1: Legal Hold Models & Core Logic
- Create `legal_hold/` app
- LegalHold model:
  - `name` (CharField - e.g., "Smith v. Jones Litigation")
  - `matter_number` (CharField, optional - legal matter/case number)
  - `description` (TextField - scope and purpose of hold)
  - `created_by` (FK to User)
  - `status` (CharField choices: DRAFT, ACTIVE, RELEASED)
  - `activated_at` (DateTimeField, nullable)
  - `released_at` (DateTimeField, nullable)
  - `released_by` (FK to User, nullable)
  - `release_reason` (TextField, nullable)
  - `created_at`, `updated_at`
- LegalHoldCriteria model:
  - `hold` (FK to LegalHold)
  - `criteria_type` (CharField choices: CUSTODIAN, DATE_RANGE, TAG, DOCUMENT_TYPE, SEARCH_QUERY, CABINET, SPECIFIC_DOCUMENTS)
  - `value` (JSONField):
    - CUSTODIAN: `{ "user_ids": [1, 2, 3] }` - documents owned/created by these users
    - DATE_RANGE: `{ "start": "2024-01-01", "end": "2024-12-31" }` - documents in date range
    - TAG: `{ "tag_ids": [5, 10] }` - documents with these tags
    - DOCUMENT_TYPE: `{ "type_ids": [2] }` - documents of these types
    - SEARCH_QUERY: `{ "query": "contract AND vendor" }` - documents matching search
    - CABINET: `{ "cabinet_ids": [3] }` - documents in these cabinets
    - SPECIFIC_DOCUMENTS: `{ "document_ids": [100, 200, 300] }` - explicit document list
  - Multiple criteria per hold (AND logic: document must match ALL criteria)
- LegalHoldCustodian model:
  - `hold` (FK to LegalHold)
  - `user` (FK to User)
  - `notified_at` (DateTimeField, nullable)
  - `acknowledged` (BooleanField, default=False)
  - `acknowledged_at` (DateTimeField, nullable)
  - `notes` (TextField, nullable)
- LegalHoldDocument model (materialized join):
  - `hold` (FK to LegalHold)
  - `document` (FK to Document)
  - `held_at` (DateTimeField, auto_now_add)
  - `released_at` (DateTimeField, nullable)
  - Unique constraint on (hold, document)
- Hold enforcement logic:
  - When hold activated:
    1. Evaluate criteria to find matching documents
    2. Create LegalHoldDocument records for each match
    3. Set `Document.is_held = True` flag (new BooleanField)
    4. Notify custodians via email
  - Held documents cannot:
    - Be deleted (soft or hard) - raise `DocumentHeldError`
    - Be modified (content/file changes blocked) - metadata changes allowed
    - Have retention policies applied (skip in retention enforcement task)
  - Hold release:
    1. Set hold status to RELEASED
    2. Remove `is_held` flag from documents (only if no other active holds apply)
    3. Record release in audit trail
  - Periodic re-evaluation (Celery task, daily):
    - For SEARCH_QUERY criteria, re-run search to catch newly matching documents
    - Add any new matches to LegalHoldDocument

### Task 22.2: Legal Hold API & Integration
- API:
  - GET/POST `/api/v1/legal_holds/` - List/create holds (admin/legal role only)
  - GET/PATCH `/api/v1/legal_holds/{id}/` - Detail/update
  - POST `/api/v1/legal_holds/{id}/activate/` - Activate hold (evaluate criteria, freeze documents)
  - POST `/api/v1/legal_holds/{id}/release/` - Release hold (requires reason)
  - GET `/api/v1/legal_holds/{id}/documents/` - List held documents
  - GET `/api/v1/legal_holds/{id}/custodians/` - List custodians with acknowledgement status
  - POST `/api/v1/legal_holds/{id}/custodians/{cid}/acknowledge/` - Custodian acknowledges hold
  - POST `/api/v1/legal_holds/{id}/notify/` - Re-send custodian notification emails
  - GET `/api/v1/legal_holds/{id}/export/` - Export hold report (CSV/PDF)
- Integration with existing systems:
  - Document delete API: check `is_held`, return 403 with explanation if held
  - Document upload API: allow uploads (new documents not frozen)
  - Retention enforcement task: skip documents where `is_held=True`
  - Audit trail: all hold actions logged via existing audit system
  - Notification system: custodian notifications via existing email channel
- Permission model:
  - New permission: `legal_hold.manage` (create, activate, release holds)
  - New permission: `legal_hold.view` (view hold details and held documents)
  - Custodians get view access to holds they're custodians of

### Task 22.3: Legal Hold Frontend
- **Legal hold dashboard** (admin/legal section):
  - Active holds with document count, custodian status
  - Draft holds pending activation
  - Released holds (history)
  - Stats: total documents under hold, total active holds
- **Create/edit hold page**:
  - Name, matter number, description fields
  - Criteria builder:
    - Add criteria rows (type selector + value input)
    - CUSTODIAN: user multi-select
    - DATE_RANGE: date range picker
    - TAG: tag multi-select
    - DOCUMENT_TYPE: type multi-select
    - SEARCH_QUERY: search box with preview of matching documents
    - CABINET: cabinet tree selector
    - SPECIFIC_DOCUMENTS: document search/picker
  - Preview: show count of documents that would be held
  - Custodian manager: add/remove users, view acknowledgement status
  - Activate button (with confirmation dialog showing document count)
- **Hold detail page**:
  - Status badge, dates, description
  - Held documents list (paginated, filterable)
  - Custodian list with acknowledgement status and timestamps
  - Audit trail timeline
  - Release button (with reason input)
  - Export report button
- **Document detail integration**:
  - "Legal Hold" badge/banner when document is held
  - List of active holds affecting this document
  - Blocked action indicators (delete, modify disabled with tooltip)

### Task 22.4: Content-Addressable Storage Backend
- ContentBlob model:
  - `sha256_hash` (CharField, primary_key=True, max_length=64)
  - `size` (BigIntegerField - file size in bytes)
  - `reference_count` (IntegerField, default=1 - number of documents referencing this blob)
  - `storage_backend` (CharField - which backend stores this blob)
  - `storage_path` (CharField - path within backend)
  - `created_at` (DateTimeField, auto_now_add)
  - `last_accessed` (DateTimeField, nullable)
- ContentAddressedStorageBackend extending StorageBackend:
  ```python
  class ContentAddressedStorageBackend(StorageBackend):
      """
      Stores files by their SHA-256 hash, automatically deduplicating
      identical content.
      """

      def save(self, name, content):
          # 1. Compute SHA-256 hash of content
          # 2. Check if ContentBlob with this hash exists
          # 3. If exists: increment reference_count, return existing path
          # 4. If not: store file at hash-based path, create ContentBlob record
          # Hash-based path: ab/cd/abcdef1234...  (first 2 chars / next 2 chars / full hash)

      def delete(self, name):
          # 1. Find ContentBlob by hash
          # 2. Decrement reference_count
          # 3. If reference_count == 0: delete physical file and ContentBlob record
          # 4. If reference_count > 0: no-op (other documents still reference it)

      def exists(self, name):
          return ContentBlob.objects.filter(sha256_hash=name).exists()

      def open(self, name, mode='rb'):
          blob = ContentBlob.objects.get(sha256_hash=name)
          blob.last_accessed = timezone.now()
          blob.save(update_fields=['last_accessed'])
          return self._backend.open(blob.storage_path, mode)

      def get_dedup_stats(self):
          # Return: total blobs, total references, storage saved
          total_refs = ContentBlob.objects.aggregate(Sum('reference_count'))
          total_blobs = ContentBlob.objects.count()
          duplicates_avoided = total_refs - total_blobs
          # Calculate space saved
  ```
- DocumentFile model changes:
  - Add `content_blob` (FK to ContentBlob, nullable) alongside existing `file` field
  - When content-addressed storage enabled, `file` field stores the hash, `content_blob` points to blob record
- Configuration:
  - `STORAGE_CONTENT_ADDRESSED=True/False` (default: False)
  - `STORAGE_CONTENT_ADDRESSED_BACKEND=local` or `s3` (underlying storage for blobs)
  - Works as a wrapper around any existing storage backend
- Integrity verification:
  - Periodic Celery task: verify stored file hashes match ContentBlob records
  - Report corruption if hash mismatch detected
  - Self-healing: if one reference is corrupted but another copy exists, restore from reference

### Task 22.5: Content-Addressable Storage Migration & Reporting
- Management command: `manage.py migrate_to_content_addressed`
  - Scan all existing DocumentFile records
  - For each file:
    1. Compute SHA-256 hash
    2. If ContentBlob exists: link to existing, increment ref count, delete duplicate file
    3. If not: create ContentBlob, move file to hash-addressed path
    4. Update DocumentFile to reference ContentBlob
  - Progress reporting (processed/total, space saved so far)
  - Dry-run mode (`--dry-run`): report what would happen without changes
  - Batch processing with configurable batch size
  - Resumable: track progress in cache, skip already-migrated files
- Storage savings dashboard widget:
  - Total documents vs unique blobs
  - Space used vs space without dedup
  - Percentage saved
  - Top duplicated files (most references)
- API:
  - GET `/api/v1/storage/dedup_stats/` - Deduplication statistics (admin)
  - POST `/api/v1/storage/verify_integrity/` - Trigger integrity check (admin)

### Task 22.6: Physical Records Models & API
- Create `physical_records/` app
- PhysicalLocation model (hierarchical):
  - `name` (CharField)
  - `location_type` (CharField choices: BUILDING, ROOM, CABINET, SHELF, BOX)
  - `parent` (FK to self, nullable - tree structure via MPTT)
  - `barcode` (CharField, unique, nullable - physical barcode label)
  - `capacity` (IntegerField, nullable - max items)
  - `current_count` (IntegerField, default=0)
  - `notes` (TextField, nullable)
  - `is_active` (BooleanField, default=True)
- PhysicalRecord model:
  - `document` (OneToOneField to Document - one physical record per digital document)
  - `location` (FK to PhysicalLocation)
  - `position` (CharField, optional - specific position within location, e.g., "Slot 3")
  - `barcode` (CharField, unique, nullable - barcode on the physical file)
  - `condition` (CharField choices: GOOD, FAIR, POOR, DAMAGED)
  - `notes` (TextField, nullable)
  - `created_at`, `updated_at`
- ChargeOut model:
  - `physical_record` (FK to PhysicalRecord)
  - `user` (FK to User - who has the physical file)
  - `checked_out_at` (DateTimeField, auto_now_add)
  - `expected_return` (DateTimeField)
  - `returned_at` (DateTimeField, nullable)
  - `notes` (TextField, nullable)
  - `status` (CharField choices: CHECKED_OUT, RETURNED, OVERDUE)
- DestructionCertificate model:
  - `physical_record` (FK to PhysicalRecord)
  - `destroyed_at` (DateTimeField)
  - `destroyed_by` (FK to User)
  - `method` (CharField choices: SHREDDING, INCINERATION, PULPING, OTHER)
  - `witness` (CharField, optional - witness name)
  - `certificate_pdf` (FileField - generated destruction certificate)
  - `notes` (TextField, nullable)
- API:
  - GET/POST `/api/v1/physical_locations/` - Location CRUD
  - GET/PATCH/DELETE `/api/v1/physical_locations/{id}/`
  - GET `/api/v1/physical_locations/{id}/tree/` - Location hierarchy
  - GET/POST `/api/v1/physical_records/` - Record CRUD
  - GET/PATCH/DELETE `/api/v1/physical_records/{id}/`
  - POST `/api/v1/documents/{id}/charge_out/` - Check out physical file
    - Body: `{ "expected_return": "2024-06-01", "notes": "For audit review" }`
    - Creates ChargeOut record, updates location current_count
  - POST `/api/v1/documents/{id}/charge_in/` - Return physical file
    - Body: `{ "notes": "Returned in good condition" }`
    - Sets returned_at on ChargeOut
  - POST `/api/v1/physical_records/{id}/barcode_checkout/` - Barcode-driven checkout
    - Body: `{ "barcode": "PHY-12345" }` - scan barcode to check out
  - GET `/api/v1/charge_outs/` - List all checkouts (filterable by status, user, date)
  - GET `/api/v1/charge_outs/overdue/` - List overdue items
  - POST `/api/v1/physical_records/{id}/destruction_certificate/` - Generate certificate
    - Body: `{ "method": "SHREDDING", "witness": "John Smith" }`
    - Generate PDF certificate, link physical record as destroyed
- Celery tasks:
  - `check_overdue_charge_outs`: Daily check for overdue physical file returns
  - Send notification to user and admin when charge-out becomes overdue
  - `generate_destruction_certificates`: Batch generate for retention-expired records

### Task 22.7: Physical Records Frontend
- **Physical location management** (admin):
  - Tree view of locations (Building > Room > Cabinet > Shelf > Box)
  - Add/edit/remove locations
  - Capacity indicators (visual fill bar)
  - Barcode display/print for locations
- **Physical record management**:
  - Add physical location to document (document detail tab: "Physical Record")
  - Location picker (hierarchical dropdown or tree selector)
  - Position field
  - Barcode field (with print label button)
  - Condition indicator
- **Charge-out management**:
  - "Check Out" / "Check In" buttons on document detail
  - Expected return date picker
  - Current status indicator (available / checked out by X / overdue)
  - Charge-out history table
- **Charge-out dashboard** (admin):
  - Currently checked out items (with who/when/expected return)
  - Overdue items (highlighted)
  - Return rate statistics
  - Search by user, location, barcode
- **Destruction certificate**:
  - "Generate Destruction Certificate" button on physical record
  - Method selector, witness field
  - Preview and confirm
  - Download generated PDF
- **Reports**:
  - Physical inventory report (location tree with contents)
  - Charge-out history report
  - Overdue items report
  - Destruction log report

---

## Dependencies

### New Python Packages
```
# reportlab already added in Sprint 21 for PDF generation
# No additional packages needed
```

### Document Model Changes
```python
# Add to Document model:
is_held = models.BooleanField(default=False, db_index=True)
```

---

## Definition of Done
- [ ] Legal holds can be created with criteria (custodian, date, tags, search query)
- [ ] Activating a hold freezes matching documents (delete/modify blocked)
- [ ] Custodian notification and acknowledgement tracking works
- [ ] Hold release unfreezes documents with audit trail
- [ ] Retention enforcement respects legal holds
- [ ] Content-addressable storage deduplicates identical files
- [ ] Migration command converts existing storage to content-addressed
- [ ] Dedup statistics dashboard shows storage savings
- [ ] Integrity verification detects corrupted files
- [ ] Physical locations can be managed in hierarchical tree
- [ ] Physical records link digital documents to physical storage
- [ ] Charge-out/charge-in tracks who has physical files
- [ ] Overdue charge-out notifications sent
- [ ] Destruction certificates generated as PDF
- [ ] All features have unit tests
- [ ] Legal hold permissions enforced (admin/legal role only)

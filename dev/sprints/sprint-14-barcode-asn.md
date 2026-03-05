# Sprint 14: Barcode Detection & ASN System

## Phase: 5 - Intelligence & AI
## Duration: 2 weeks
## Prerequisites: Sprint 13 (ML Classification Pipeline)

---

## Sprint Goal
Implement barcode detection for document splitting, Archive Serial Number (ASN) extraction, and tag extraction from barcodes. Build the complete ASN management system for bridging physical and digital document archives.

---

## Context for Agents

### Read Before Starting
- `/doc/product-spec.md` - Section 2.3 (Processing Module - BarcodePlugin)
- `/doc/research/paperless-ngx-analysis.md` - Section 6 (Barcode Detection & ASN System)

---

## Tasks

### Task 14.1: BarcodePlugin Implementation
- BarcodePlugin (order 20, runs before parsing)
- zxing-cpp integration for barcode detection
- Supported formats: Code128, QR, UPC-A, UPC-E, EAN-8, EAN-13, DataMatrix
- Page-by-page scanning with configurable DPI and upscaling
- Configurable max pages to scan (default: 5)

### Task 14.2: Document Splitting via Separator Barcodes
- Configurable separator barcode string (default: "PATCH T")
- When separator detected: split document at barcode page
- Each resulting segment submitted as separate document to processing pipeline
- Option to retain or discard separator pages
- Celery task for processing split documents

### Task 14.3: ASN Barcode Extraction
- Configurable ASN prefix (e.g., "ASN")
- Extract numeric value after prefix from barcode
- Auto-assign to document's archive_serial_number field
- Duplicate ASN prevention (skip if ASN already exists)
- ASN auto-generation option (next available number)

### Task 14.4: Tag Barcode Extraction
- Configurable tag barcode mapping (regex pattern -> tag name)
- Extract tag names from barcode content
- Auto-create tags if they don't exist
- Each unique tag barcode can split document (configurable)

### Task 14.5: ASN Management UI
- ASN display in document detail and document list
- ASN search in global search
- ASN filter in document list
- Bulk ASN assignment
- Next available ASN display
- ASN label generation (printable barcode labels)
- Barcode configuration page (admin)

---

## Dependencies

### New Python Packages
```
zxing-cpp>=2.2
```

---

## Definition of Done
- [ ] Barcodes detected from PDF pages
- [ ] Separator barcodes split multi-document scans
- [ ] ASN extracted from barcodes and assigned to documents
- [ ] Tag barcodes extract and create tags
- [ ] Duplicate ASN prevention works
- [ ] Barcode configuration (DPI, formats, prefix) works
- [ ] ASN displayed and searchable in frontend
- [ ] All features have unit tests

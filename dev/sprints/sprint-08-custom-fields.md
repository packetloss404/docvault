# Sprint 8: Custom Fields & Metadata

## Phase: 3 - Organization & Search
## Duration: 2 weeks
## Prerequisites: Sprint 7 (Tags, Correspondents & Cabinets)

---

## Sprint Goal
Implement the custom fields system (12 data types) and the structured metadata system with validators, parsers, and lookups. Create per-document-type field assignments and the frontend editors.

---

## Context for Agents

### Read Before Starting
- `/doc/product-spec.md` - Section 2.2 (Organization Module - Custom Fields)
- `/doc/research/paperless-ngx-analysis.md` - Custom fields (10 types) pattern
- `/doc/research/mayan-edms-analysis.md` - MetadataType with validators/parsers

---

## Tasks

### Task 8.1: CustomField Model (12 Types)
- CustomField model with data_type choices:
  STRING, LONGTEXT, URL, DATE, DATETIME, BOOLEAN, INTEGER, FLOAT, MONETARY, DOCUMENTLINK, SELECT, MULTISELECT
- `extra_data` JSONField for type-specific config (e.g., select options)
- Per-document-type assignment (M2M through DocumentTypeCustomField)

### Task 8.2: CustomFieldInstance Model
- Per-document custom field values
- Multi-column value storage: value_text, value_bool, value_url, value_date, value_datetime, value_int, value_float, value_monetary, value_document_ids (JSON), value_select
- Property `value` that returns the correct column based on field type
- Validation on save based on field type

### Task 8.3: MetadataType Model (Mayan Pattern)
- MetadataType: name, label, default (template), lookup (template), validation (dotted path), parser (dotted path)
- DocumentMetadata: per-document metadata instances with validation
- Per-document-type metadata assignment (M2M)
- Built-in validators: regex, numeric range, date format, required
- Lookup template rendering for dropdown population

### Task 8.4: Custom Field APIs
- CustomField CRUD ViewSet
- CustomFieldInstance nested under Document ViewSet
- Bulk set custom fields on multiple documents
- Custom field query parser for complex filtering:
  `?custom_fields={"field_name": "invoice_number", "op": "contains", "value": "2026"}`
- MetadataType CRUD ViewSet
- DocumentMetadata nested ViewSet

### Task 8.5: Frontend Custom Field Editors
- Custom field editor component (renders appropriate input for each type)
- Custom field display in document detail (Metadata tab)
- Custom field columns in document list (optional, configurable)
- Custom field filter builder (per-type appropriate filter UI)
- MetadataType admin page for creating/editing metadata types
- DocumentType editor: assign custom fields and metadata types

---

## Definition of Done
- [ ] CustomField model with 12 data types works
- [ ] CustomFieldInstance stores values with proper type validation
- [ ] MetadataType with validators, parsers, lookups works
- [ ] Per-document-type field/metadata assignment works
- [ ] Custom field CRUD API works
- [ ] Custom field query parser handles complex filters
- [ ] Frontend custom field editors render correct input types
- [ ] Document detail shows custom fields and metadata
- [ ] Document list can display custom field columns
- [ ] All features have unit tests

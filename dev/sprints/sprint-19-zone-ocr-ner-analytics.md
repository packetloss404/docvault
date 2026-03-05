# Sprint 19: Zone OCR, Named Entity Recognition & Search Analytics

## Phase: 7 - Advanced Features
## Duration: 2 weeks
## Prerequisites: Sprint 18 (UI Polish, Deployment & Documentation)

---

## Sprint Goal
Implement three high-value features identified from extended market analysis: Zone OCR for structured field extraction from forms, Named Entity Recognition (NER) as searchable facets, and search analytics with relevance tuning tools.

---

## Context for Agents

### Read Before Starting
- `/doc/product-spec.md` - Section 2.3 (Processing Module - Zone OCR), Section 2.4 (Search Module - NER & Search Analytics)
- `/doc/architecture.md` - Section 4 (Processing Pipeline) and Section 7 (Search Architecture)
- `/doc/research/extended-market-analysis.md` - Features #2, #4, #7
- `/doc/sprints/sprint-05-parsers-ocr.md` - Existing OCR pipeline
- `/doc/sprints/sprint-09-search-views.md` - Existing Elasticsearch integration
- `/doc/sprints/sprint-15-llm-vector-search.md` - Existing AI plugin

---

## Tasks

### Task 19.1: Zone OCR Models & Template Designer API
- Create `zone_ocr/` app
- ZoneOCRTemplate model:
  - `name` (CharField)
  - `description` (TextField, optional)
  - `sample_page_image` (ImageField - uploaded sample form page)
  - `page_number` (IntegerField, default=1 - which page the zones apply to)
  - `created_by` (FK to User)
  - `created_at`, `updated_at` (DateTimeField)
  - `is_active` (BooleanField, default=True)
- ZoneOCRField model:
  - `template` (FK to ZoneOCRTemplate)
  - `name` (CharField - e.g., "invoice_number", "vendor_name")
  - `field_type` (CharField choices: STRING, DATE, INTEGER, FLOAT, MONETARY, BOOLEAN)
  - `bounding_box` (JSONField - {x, y, width, height} as percentages of page dimensions)
  - `custom_field` (FK to CustomField, optional - auto-populate this custom field)
  - `order` (IntegerField)
  - `preprocessing` (CharField choices: NONE, NUMERIC_ONLY, ALPHA_ONLY, DATE_PARSE, CURRENCY_PARSE)
  - `validation_regex` (CharField, optional)
- ZoneOCRResult model:
  - `document` (FK to Document)
  - `template` (FK to ZoneOCRTemplate)
  - `field` (FK to ZoneOCRField)
  - `extracted_value` (TextField)
  - `confidence` (FloatField, 0.0-1.0)
  - `reviewed` (BooleanField, default=False)
  - `reviewed_by` (FK to User, nullable)
  - `corrected_value` (TextField, nullable)
- API:
  - GET/POST `/api/v1/zone_ocr_templates/` (CRUD)
  - GET/PATCH/DELETE `/api/v1/zone_ocr_templates/{id}/`
  - GET/POST `/api/v1/zone_ocr_templates/{id}/fields/` (manage fields)
  - POST `/api/v1/zone_ocr_templates/{id}/test/` (test template against a document)
  - GET `/api/v1/zone_ocr_results/` (filterable by document, template, confidence, reviewed)
  - PATCH `/api/v1/zone_ocr_results/{id}/` (submit corrections)

### Task 19.2: Zone OCR Processing Plugin
- ZoneOCRPlugin (order 107, runs after OCRPlugin, before ClassificationPlugin):
  ```python
  class ZoneOCRPlugin(ProcessingPlugin):
      name = "zone_ocr"
      order = 107

      def can_run(self, context):
          # Only run if zone OCR templates exist and document has pages
          return ZoneOCRTemplate.objects.filter(is_active=True).exists()

      def process(self, context):
          # 1. Render document page to image (if not already image)
          # 2. For each active template, compute similarity score against sample
          # 3. Pick best-matching template (above threshold)
          # 4. For each field in template:
          #    a. Crop bounding box region from page image
          #    b. Run OCR on cropped region (Tesseract with PSM mode tuned for field type)
          #    c. Apply preprocessing (numeric_only, date_parse, etc.)
          #    d. Validate against regex if configured
          #    e. Compute confidence score
          #    f. Store ZoneOCRResult
          # 5. For fields mapped to custom fields, auto-populate CustomFieldInstance
          # 6. Queue low-confidence results for human review
  ```
- Template matching algorithm:
  - Use structural similarity (SSIM) or perceptual hashing on page layout
  - Compare against all active templates, pick highest score above threshold (0.7 default)
  - Configurable threshold via `ZONE_OCR_MATCH_THRESHOLD` env var
- Tesseract PSM modes per field type:
  - STRING: PSM 7 (single line)
  - INTEGER/FLOAT/MONETARY: PSM 7 + digits-only whitelist
  - DATE: PSM 7 + date character whitelist
- Confidence calculation: Tesseract word confidence averaged across extracted region

### Task 19.3: Zone OCR Frontend
- Template designer page (admin):
  - Upload sample form image
  - Canvas overlay for drawing bounding boxes (drag to create, resize handles)
  - Name each zone and assign field type
  - Map zones to custom fields (dropdown)
  - Save/load templates
  - Test template against existing document (show extracted values inline)
- Review queue page:
  - List low-confidence extractions (< configurable threshold, default 0.8)
  - Show cropped region image alongside extracted text
  - Inline correction with accept/reject buttons
  - Bulk accept for high-confidence batches
  - Filter by template, date range, confidence range
- Document detail integration:
  - "Zone OCR" tab showing extracted fields from matched template
  - Visual overlay of zones on document preview

### Task 19.4: Named Entity Recognition Plugin & Models
- Create `entities/` app (or add to existing `search/` app)
- EntityType model:
  - `name` (CharField - PERSON, ORGANIZATION, LOCATION, DATE, MONETARY, CUSTOM)
  - `label` (CharField - display name)
  - `color` (CharField - hex color for UI)
  - `extraction_pattern` (TextField, optional - custom regex for domain-specific entities)
  - `enabled` (BooleanField, default=True)
  - `icon` (CharField - icon name for UI)
- Entity model:
  - `document` (FK to Document)
  - `entity_type` (FK to EntityType)
  - `value` (CharField - the extracted text, normalized)
  - `raw_value` (CharField - original text as found in document)
  - `confidence` (FloatField, 0.0-1.0)
  - `start_offset` (IntegerField - character position in content)
  - `end_offset` (IntegerField)
  - `page_number` (IntegerField, optional)
- NERPlugin (order 115, after AIPlugin):
  ```python
  class NERPlugin(ProcessingPlugin):
      name = "ner"
      order = 115

      def process(self, context):
          # 1. Load spaCy model (en_core_web_trf or configurable)
          # 2. Process document content through NER pipeline
          # 3. For each detected entity:
          #    a. Normalize value (title case for names, standardize dates, etc.)
          #    b. Create Entity record
          # 4. Apply custom regex patterns from EntityType.extraction_pattern
          # 5. Index entities in Elasticsearch (nested object in document mapping)
  ```
- spaCy integration:
  - Default model: `en_core_web_sm` (small, fast) or `en_core_web_trf` (accurate)
  - Configurable via `NER_SPACY_MODEL` env var
  - Entity type mapping: spaCy labels -> DocVault EntityType
  - Custom entity patterns via EntityRuler (for domain-specific terms)
- Elasticsearch entity indexing:
  - Add `entities` nested field to document mapping:
    ```json
    "entities": {
      "type": "nested",
      "properties": {
        "type": { "type": "keyword" },
        "value": { "type": "keyword" },
        "value_text": { "type": "text" }
      }
    }
    ```
  - Faceted search via nested aggregations

### Task 19.5: NER Frontend & Entity Browser
- Entity browser page:
  - Faceted sidebar: filter by entity type (PERSON, ORG, LOCATION, etc.)
  - Entity list: show all unique entities with document count
  - Click entity to see all documents containing it
  - Search within entities
- Entity co-occurrence graph:
  - Network visualization (D3.js or vis.js)
  - Nodes = entities, edges = co-occurrence in same document
  - Node size = document count, edge weight = co-occurrence frequency
  - Filter by entity type, minimum co-occurrence count
  - Click node to drill down to documents
- Document detail integration:
  - "Entities" tab showing extracted entities grouped by type
  - Highlight entities in document content view
  - Click entity to search for all related documents
- Search integration:
  - Entity facets in search sidebar
  - Entity-based filter rules in saved views
  - Typeahead suggestions include entity matches

### Task 19.6: Search Analytics Models & Dashboard
- SearchQuery model:
  - `query_text` (CharField)
  - `user` (FK to User)
  - `results_count` (IntegerField)
  - `clicked_document` (FK to Document, nullable - first clicked result)
  - `click_position` (IntegerField, nullable - rank of clicked result)
  - `timestamp` (DateTimeField, auto_now_add)
  - `response_time_ms` (IntegerField)
- SearchSynonym model:
  - `terms` (ArrayField of CharField - list of synonymous terms)
  - `enabled` (BooleanField, default=True)
  - `created_by` (FK to User)
- SearchCuration model:
  - `query_text` (CharField - the query this curation applies to)
  - `pinned_documents` (M2M to Document - always show first)
  - `hidden_documents` (M2M to Document - never show)
  - `boost_fields` (JSONField, optional - per-field boost overrides)
  - `enabled` (BooleanField, default=True)
- Search query logging middleware:
  - Intercept search API calls
  - Log query, results count, response time
  - Track clicks via separate endpoint: POST `/api/v1/search/click/`
- API:
  - GET `/api/v1/search/analytics/` - Dashboard data (admin only):
    - Top 50 queries (last 7/30/90 days)
    - Zero-result queries (last 7/30/90 days)
    - Average click-through rate
    - Average click position (lower = better relevance)
    - Query volume over time
  - GET/POST `/api/v1/search/synonyms/` - Synonym CRUD
  - GET/POST `/api/v1/search/curations/` - Curation CRUD
  - POST `/api/v1/search/click/` - Track result click

### Task 19.7: Search Analytics Frontend & Synonym/Curation Admin
- Search analytics dashboard (admin page):
  - Top queries bar chart
  - Zero-result queries table (with "create curation" action)
  - Click-through rate trend line
  - Average click position gauge
  - Date range selector (7d, 30d, 90d, custom)
- Synonym management page (admin):
  - List synonym groups
  - Add/edit/delete synonym groups
  - Preview: show how a query would be expanded
- Curation management page (admin):
  - List curations
  - Create curation: enter query, search for documents to pin/hide
  - Drag-and-drop ordering for pinned results
- Elasticsearch integration:
  - Apply synonyms via synonym token filter on search
  - Apply curations by injecting pinned/hidden doc IDs into query
  - Apply relevance boosts from curations

---

## Dependencies

### New Python Packages
```
spacy>=3.7
Pillow>=10.0 (already likely present)
scikit-image>=0.22 (for SSIM template matching)
```

### spaCy Model Download
```
python -m spacy download en_core_web_sm
```

---

## Definition of Done
- [ ] Zone OCR templates can be created with visual bounding box designer
- [ ] Zone OCR plugin auto-detects matching template and extracts fields
- [ ] Low-confidence extractions queue for human review
- [ ] User corrections feed back into accuracy improvement
- [ ] NER plugin extracts persons, organizations, locations, dates, amounts
- [ ] Entities indexed as structured facets in Elasticsearch
- [ ] Entity browser allows faceted browsing and co-occurrence graph
- [ ] Search analytics track query volume, zero-result queries, click-through
- [ ] Synonym management allows admin to define synonym groups
- [ ] Curations allow pinning/hiding results for specific queries
- [ ] All features have unit tests
- [ ] Features gracefully degrade when dependencies unavailable

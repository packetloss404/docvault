# Sprint 7: Tags, Correspondents & Cabinets

## Phase: 3 - Organization & Search
## Duration: 2 weeks
## Prerequisites: Sprint 6 (Thumbnails, Versions & Non-Destructive Mode)

---

## Sprint Goal
Build the complete organizational system: hierarchical tags (MPTT with colors), correspondents with matching algorithms, hierarchical cabinets (MPTT), and storage paths with Jinja2 templates. Create all CRUD APIs and frontend management pages.

---

## Context for Agents

### Read Before Starting
- `/doc/product-spec.md` - Section 2.2 (Organization Module)
- `/doc/research/paperless-ngx-analysis.md` - Hierarchical tags, matching algorithms
- `/doc/research/mayan-edms-analysis.md` - MPTT cabinets pattern

---

## Tasks

### Task 7.1: Organization App & Tag Model
- Create `organization/` app
- Tag model: MPTT TreeNodeModel with parent, color (hex), is_inbox_tag flag
- Max nesting depth: 5 levels
- Unique label enforcement (per-level siblings)
- MatchingModel base class with matching_algorithm field
- Tag inherits from MatchingModel + TreeNodeModel + OwnedModel

### Task 7.2: Correspondent & StoragePath Models
- Correspondent model extends MatchingModel + OwnedModel
- StoragePath model extends MatchingModel + OwnedModel with `path` template field
- Jinja2-based path template rendering: `{{ created_year }}/{{ correspondent }}/{{ title }}`
- Path template validation on save

### Task 7.3: Matching Algorithm Implementation
- Implement all 7 matching algorithms in `organization/matching.py`:
  - MATCH_NONE (0): Never auto-match
  - MATCH_ANY (1): Any word from match pattern present in content
  - MATCH_ALL (2): All words from match pattern present
  - MATCH_LITERAL (3): Exact string match in content
  - MATCH_REGEX (4): Regex pattern match
  - MATCH_FUZZY (5): Fuzzy/approximate word matching (ratio > 0.85)
  - MATCH_AUTO (6): ML-based (placeholder, implemented in Sprint 13)

### Task 7.4: CRUD APIs for All Organization Models
- Tag ViewSet with hierarchy support (nested serializer showing children)
- Correspondent ViewSet
- Cabinet ViewSet with tree operations (move, reparent)
- StoragePath ViewSet
- Bulk operations: bulk assign tags/correspondent to documents
- Autocomplete endpoints for each model

### Task 7.5: Frontend Management Pages
- Tag management page: tree view, create, edit, delete, color picker
- Correspondent management page: list, create, edit, delete
- Cabinet management page: tree view with drag-and-drop reordering
- Tag assignment in document detail page (autocomplete multi-select)
- Correspondent assignment in document detail (autocomplete dropdown)
- Cabinet assignment (move document into cabinet)

---

## Definition of Done
- [ ] Tag model with MPTT hierarchy, colors, and matching works
- [ ] Correspondent model with matching algorithms works
- [ ] Cabinet model with MPTT hierarchy works
- [ ] StoragePath model with Jinja2 templates works
- [ ] All 6 matching algorithms implemented and tested
- [ ] CRUD APIs for all organization models work
- [ ] Bulk tag/correspondent assignment works
- [ ] Autocomplete endpoints work
- [ ] Frontend tag, correspondent, cabinet pages work
- [ ] Document detail page shows tags, correspondent, cabinets
- [ ] All features have unit tests

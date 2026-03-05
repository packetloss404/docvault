# Sprint 9: Search & Saved Views

## Phase: 3 - Organization & Search
## Duration: 2 weeks
## Prerequisites: Sprint 8 (Custom Fields & Metadata)

---

## Sprint Goal
Integrate Elasticsearch for full-text search with faceted filtering, build saved views with customizable display modes, and create the frontend search UI with global search, filter builder, and dashboard widgets.

---

## Context for Agents

### Read Before Starting
- `/doc/architecture.md` - Section 7 (Search Architecture)
- `/doc/product-spec.md` - Section 2.4 (Search Module)
- `/doc/research/paperless-ngx-analysis.md` - Whoosh/FAISS search, saved views
- We use Elasticsearch instead of Whoosh for better scalability

---

## Tasks

### Task 9.1: Elasticsearch Integration
- Elasticsearch client configuration (elasticsearch-py)
- Index schema (see architecture.md Section 7 for full schema)
- Index management: create, update mapping, rebuild
- Document indexing: index on create/update, remove on delete
- Full-text search with BM25 scoring
- Faceted aggregations (tags, correspondent, document type, date ranges)
- Search highlighting on content and title matches
- Permission-aware filtering (index owner_id, filter in query)
- Celery task for index rebuild
- Celery task for index optimization (daily)

### Task 9.2: Search API
- GET `/api/v1/search/?query=...` - Full-text search
- GET `/api/v1/search/autocomplete/?query=...` - Typeahead suggestions
- GET `/api/v1/search/similar/{id}/` - "More like this" (Elasticsearch MLT query)
- Support field-specific queries: `tag:invoice`, `correspondent:acme`
- Date range queries: `created:[2025-01-01 TO 2025-12-31]`
- Pagination on search results
- Highlight snippets in results
- Aggregation counts in response (tag facets, type facets, date histogram)

### Task 9.3: Saved View Model & API
- SavedView model:
  - name, display_mode (TABLE/SMALL_CARDS/LARGE_CARDS)
  - display_fields (JSONField - list of column names)
  - sort_field, sort_reverse
  - page_size
  - show_on_dashboard, show_in_sidebar
  - owner (per-user views)
- SavedViewFilterRule model:
  - saved_view (FK), rule_type, value
  - Support 48+ rule types (title contains, tags include, date after, etc.)
- SavedView CRUD API
- Execute saved view (apply filters, return results)

### Task 9.4: Frontend Global Search
- Global search component (Ctrl+K shortcut to open)
- Real-time typeahead across documents, tags, correspondents, types
- Search results page with highlighting
- Quick navigation to document detail from results
- Recent searches history (localStorage)
- Advanced query syntax help tooltip

### Task 9.5: Frontend Filter Builder
- Visual filter builder component
- Add/remove filter rules
- Rule types: text contains, tag is, correspondent is, document type is, date range, ASN range, custom field value, has notes, is shared
- AND/OR logic between rules
- Save current filters as a new saved view

### Task 9.6: Frontend Dashboard with Saved Views
- Dashboard component with widget grid
- Saved view widgets showing filtered document lists
- Statistics widget (total documents, recent, by type)
- Quick upload widget (drag-and-drop)
- Saved views in sidebar navigation
- Per-user dashboard customization (widget order, visibility)

---

## Dependencies

### New Python Packages
```
elasticsearch>=8.0
```

### Docker Compose Additions
```yaml
elasticsearch:
  image: elasticsearch:8.15.0
  environment:
    - discovery.type=single-node
    - xpack.security.enabled=false
    - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
  ports:
    - "9200:9200"
  volumes:
    - esdata:/usr/share/elasticsearch/data
```

---

## Definition of Done
- [ ] Elasticsearch indexes documents with full schema
- [ ] Full-text search returns relevant results with highlighting
- [ ] Faceted search works (tags, type, date, correspondent)
- [ ] Search autocomplete endpoint works
- [ ] "More like this" similar document search works
- [ ] Saved views can be created with filter rules
- [ ] Saved views execute and return filtered results
- [ ] Frontend global search (Ctrl+K) works
- [ ] Frontend filter builder works
- [ ] Dashboard shows saved view widgets and statistics
- [ ] All features have unit tests

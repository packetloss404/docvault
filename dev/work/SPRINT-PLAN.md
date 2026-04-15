# Integration Sprint Plan

**Generated:** 2026-04-15
**Scope:** Resolve all missing frontend integrations and backend gaps identified by 10-agent audit.
**Structure:** 2 sprints across 4 domains, ~40 tasks total.

---

## Sprint 1 — "Wire & Surface" (Quick wins, high-impact, lower-risk)

### Domain A: Document-Detail Integration (Planner 1)

| # | Task | Complexity | Files |
|---|------|-----------|-------|
| A1.1 | **Legal hold banner** — Inject `LegalHoldService`, show red alert above tabs when `is_held` | S | `document-detail.component.ts`, `.html` |
| A1.2 | **Comments + checkout/share on Details tab** — Wire `CommentsComponent` + `CollaborationService` (checkout status, check-in actions, share-link creation) | M | `document-detail.component.ts`, `.html` |
| A1.3 | **Signatures tab** — Add `'signatures'` tab, mount `DocumentSignaturesComponent` | S | `document-detail.component.ts`, `.html` |
| A1.4 | **ML suggestions on Details tab** — Mount `SuggestionPanelComponent` above custom fields | S | `document-detail.component.ts`, `.html` |
| A1.5 | **Relationships on Details tab** — Mount `RelationshipPanelComponent` + "View Graph" link to `/documents/:id/graph` | S | `document-detail.component.ts`, `.html` |

**Dependencies:** All tasks are independent and can be parallelized.

---

### Domain B: Search, Analytics & Admin (Planner 2)

| # | Task | Complexity | Files |
|---|------|-----------|-------|
| B1.1 | **Wire `trackClick` in search-results** — Inject `AnalyticsService`, call `trackClick({ query, document_id, position })` on click + middle-click | S | `search-results.component.ts`, `.html` |
| B1.2 | **CTR display in search-analytics** — Expose existing `click_through_rate` + `avg_click_position` in template | S | `search-analytics.component.ts`, `.html` |
| B1.3 | **RBAC service methods** — Add `getUsers/Groups/Roles/Permissions()` to `security.service.ts` + interfaces to `security.model.ts` | M | `security.service.ts`, `security.model.ts` |
| B1.4 | **403 guard + nav hiding** — Extend `auth.guard.ts` for permission checks, hide admin nav in layout | S | `auth.guard.ts`, `layout.component.ts`, `.html` |
| B1.5 | **Backend: wire `index_document` signal** — Connect `post_save`/`post_delete` on `Document` to Celery `index_document` task | M | `documents/signals.py`, `documents/tasks.py`, `documents/apps.py` |

**Dependencies:** B1.3 before Sprint 2 RBAC admin pages.

---

### Domain C: Navigation, Org & Storage (Planner 3)

| # | Task | Complexity | Files |
|---|------|-----------|-------|
| C1.1 | **Sidebar grouping (FEAT-NG-015)** — Rewrite flat sidebar into collapsible labeled sections (Documents, Organize, Workflows, Ingest, Signatures, Analytics, Compliance, Admin). Persist state in localStorage | M | `layout.component.html`, `layout.component.ts` |
| C1.2 | **Search-scope rule** — Document the rule: global search = `/search`, list filter = query params on `/documents`, saved-view = `/saved-views/:id/results` | S | `layout.component.ts`, `app.routes.ts` (comments) |
| C1.3 | **Cross-links from document detail** — Add Relationships/Graph buttons linking to existing routes | S | `document-detail.component.html`, `.ts` |
| C1.4 | **Storage admin component (FEAT-NG-013)** — New `storage-admin` component with dedup-stats panel + verify-integrity action. Route: `/admin/storage` | M | New component, `app.routes.ts` |
| C1.5 | **Kill bulk-ops dead code (FEAT-NG-014)** — **WONTFIX** — Remove unused `bulkAssign()` and `bulkSetCustomFields()` from `organization.service.ts` | S | `organization.service.ts` |

**Dependencies:** C1.1 should land before C1.4 (admin sidebar group needed for route).

---

### Domain D: Backend & Infrastructure (Planner 4)

| # | Task | Complexity | Files |
|---|------|-----------|-------|
| D1.1 | **Legal hold mutation guard** — Add `HTTP 409` block on `Document` update/destroy when `is_held`, unless caller holds `legal_hold.override` permission | M | `documents/views.py`, `security/permissions.py` |
| D1.2 | **Celery Beat schedule** — Add entries: workflow escalations (5m), scheduled rules (15m), mail poll (5m), retention (daily), ES optimize (nightly) | M | `celery.py`, `settings/base.py` |
| D1.3 | **SELECT field type for workflow transitions** — Add `FIELD_TYPE_SELECT` + `choices` JSON field | S | `workflows/constants.py`, `workflows/models/`, migration |
| D1.4 | **Document.is_obsolete + supersede effect** — Bool field, auto-set on "supersedes" relationship create | M | `documents/models/document.py`, `relationships/views.py`, migration |
| D1.5 | **DocumentFile FK to CAS blob** — Add nullable `blob` FK to `storage.ContentBlob` | M | `documents/models/document.py`, migration |
| D1.6 | **CAS migration command** — `migrate_to_cas` management command: iterate files, compute SHA-256, create/link blobs | M | New: `documents/management/commands/migrate_to_cas.py` |
| D1.7 | **OIDC/SSO backend wiring** — Add `allauth` OIDC provider config driven by env vars | M | `settings/base.py`, `urls.py` |
| D1.8 | **Django SPA deep-link fallback** — Catch-all URL serving `index.html` for Angular routes | S | `urls.py` |
| D1.9 | **Transition shape alignment** — Ensure `POST .../transition/` accepts `{transition_id, field_values}`, returns `{instance_id, current_state, log_id}` | S | `workflows/views.py`, `workflows/serializers.py` |

**Dependencies:** D1.1 enables A1.1 (legal hold banner). D1.5 before D1.6.

---

## Sprint 2 — "Complex & Polish" (New UI, dependent features, stretch goals)

### Domain A: Document-Detail Integration (Planner 1)

| # | Task | Complexity | Files |
|---|------|-----------|-------|
| A2.1 | **AI tab (chat + similar docs + health)** — New `'ai'` tab. Mount `DocumentChatComponent` + `SimilarDocumentsComponent`. Check `AIService.getStatus()` and show degraded UI when unhealthy | L | `document-detail.component.ts`, `.html` |
| A2.2 | **Annotation toolbar + panel in Preview tab** — Restructure Preview to two-column: iframe + annotation panel. Mount toolbar above iframe | L | `document-detail.component.ts`, `.html` |
| A2.3 | **E-signature request flow** — "Request Signature" button in Details header, modal form calling `EsignatureService.createRequest()`, status badges | M | `document-detail.component.ts`, `.html` |
| A2.4 | **Zone OCR tab** — New `'zone-ocr'` tab with template selector, "Run OCR" action, results table | M | `document-detail.component.ts`, `.html` |
| A2.5 | **Physical Record tab** — New `'physical'` tab showing location, barcode, charge-out status, deep link to `/physical-locations` | S | `document-detail.component.ts`, `.html` |

**Dependencies:** A2.3 after A1.3 (signatures tab for visual separation). Expand `activeTab` union from 5→9 values at sprint start.

---

### Domain B: Search, Analytics & Admin (Planner 2)

| # | Task | Complexity | Files |
|---|------|-----------|-------|
| B2.1 | **RBAC admin pages** — New components: `admin-users/`, `admin-groups/`, `admin-roles/` with list + form. Routes: `/admin/users`, `/admin/groups`, `/admin/roles`. Permission-guarded | M | New components, `app.routes.ts` |
| B2.2 | **Ctrl+K global search overlay** — New `global-search-overlay` in `layout.component`. Cross-entity typeahead, recent queries (localStorage, max 10) | M | New component, `layout.component.ts` |
| B2.3 | **Rich filter builder on search page** — New sub-component `search-filter-builder` with field/operator/value rows, structured filter output | M | New component, `search-results.component.html` |
| B2.4 | **OR filter groups for saved views** — Extend saved-views filter form with grouped OR logic. Update `SavedView` model | M | `saved-views.component.ts`, `search.model.ts` |
| B2.5 | **Entity co-occurrence graph + facets in search** — D3/SVG force-graph in entity-browser, entity facet section in search-results | L | `entity-browser.component.ts`, `search-results.component.ts`, `entity.service.ts` |
| B2.6 | **Automatic query logging + response-time metrics** — Record timing in `SearchService.search()`, fire `AnalyticsService.trackQuery()` | S | `analytics.service.ts`, `search.service.ts` |

**Dependencies:** B2.1 requires B1.3. B2.3/B2.4 benefit from B1.5 (indexed documents).

---

### Domain C: Navigation, Org & Storage (Planner 3)

| # | Task | Complexity | Files |
|---|------|-----------|-------|
| C2.1 | **Tag tree depth enforcement** — Client-side depth check (max 5) on create/move, inline error | S | `tags.component.ts`, `.html` |
| C2.2 | **StoragePath autocomplete** — Add `autocompleteStoragePath(q)` to `organization.service.ts`, wire datalist into document-detail | S | `organization.service.ts`, `document-detail.component.*` |
| C2.3 | **Cabinet drag-and-drop reorder** — CDK `DragDropModule`, drag handle per row, PATCH order on drop | M | `cabinets.component.ts`, `.html` |
| C2.4 | **Document type custom-field editor** — New `doctype-editor` component for managing custom-field assignments per doc type. Route: `/metadata-types/:id/edit` | M | New component, `app.routes.ts` |
| C2.5 | **Physical record deep link** — Add "Physical Record" link/tab on document-detail to `/physical-locations?document=:id` | S | `document-detail.component.*`, `physical-locations.component.ts` |

**Dependencies:** C2.2 touches document-detail (coordinate with Domain A changes).

---

### Domain D: Backend & Infrastructure (Planner 4)

| # | Task | Complexity | Files |
|---|------|-----------|-------|
| D2.1 | **Azure OpenAI provider** — New `azure_client.py` implementing `LLMClient`, register in factory | M | `ai/client.py`, `ai/constants.py`, new `ai/providers/azure_client.py` |
| D2.2 | **Redis stem cache** — Wrap stem lookups with `django.core.cache` (Redis), TTL 24h | S | `ml/` stemmer module |
| D2.3 | **Printable ASN/barcode label** — `GET /api/v1/documents/{id}/barcode-label/` returning PNG via `python-barcode` | M | `documents/views.py`, `documents/urls.py` |
| D2.4 | **Dockerfile dev multi-stage parity** — Align dev Dockerfile app list with production | S | `Dockerfile` |
| D2.5 | **i18n groundwork** — `ng add @angular/localize`, configure 4 locale builds, extract strings, skeleton `.xlf` files | L | `angular.json`, `src-ui/src/locale/*` |
| D2.6 | **Bulk ZIP export** — `POST /api/v1/documents/bulk-export/` streaming ZIP of originals | M | `documents/views.py`, `documents/urls.py` |

---

## Wontfix / Deferred Items

| Item | Decision | Rationale |
|------|----------|-----------|
| FEAT-NG-014 bulk-ops UI | **WONTFIX** | No UI exists, complexity vs payoff unfavorable. Remove dead service methods. |
| Visual workflow designer | **DEFERRED** | Pure frontend canvas; large effort, no backend dependency. Separate epic. |
| Dashboard drag-drop (CDK) | **DEFERRED** | Frontend-only, low priority vs integration work. |
| User-facing docs tree | **DEFERRED** | Content/docs work, not code. |
| s6-overlay in Dockerfile | **WONTFIX** | Container-per-process model (compose/K8s) makes s6 redundant. |
| ShareLinkBundle | **WONTFIX** | `ShareLink` is complete. Multi-doc bundles have no spec or model. Remove from checklist. |
| Mail OAuth refresh e2e | **DEFERRED** | Requires registered OAuth app on Gmail/Outlook. Stub task; document as operator responsibility. |
| Role-based nav visibility (NG-015 optional) | **DEFERRED** | No auth-role signals in current service layer. Revisit after RBAC admin ships. |

---

## Summary

| Metric | Sprint 1 | Sprint 2 | Total |
|--------|----------|----------|-------|
| Tasks | 24 | 18 | **42** |
| New components | 1 | 6 | **7** |
| New backend files | 2 | 2 | **4** |
| Estimated effort | 8-10 dev days | 10-14 dev days | **18-24 dev days** |

### Sprint 1 unlocks Sprint 2:
- Legal hold backend guard (D1.1) enables frontend banner (A1.1)
- RBAC service methods (B1.3) enable admin pages (B2.1)
- Sidebar grouping (C1.1) provides admin section for new routes
- Elasticsearch signal wiring (B1.5) makes search features useful end-to-end

### Document-detail tab growth:
- Current: 5 tabs (Details, Content, Preview, Metadata, Workflows)
- After Sprint 1: 6 tabs (+Signatures)
- After Sprint 2: 9 tabs (+AI, Zone OCR, Physical)
- Sections added to Details tab: Comments, Checkout, Share, ML Suggestions, Relationships

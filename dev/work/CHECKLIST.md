# Open work checklist

**Agents:** read **[`../AGENTS.md`](../AGENTS.md)** before editing. Check off lines here when merged; use **[`features/`](features/)** for § **A** acceptance detail.

---

## A — NextGen (UI / contract follow-ups)

Source: `work/features/FEAT-NG-*.md`

### FEAT-NG-007 — Document collaboration (Sprint 16 theme)

- [x] Document detail: comments thread (read + add) for `documents/:id`.
- [x] Document detail: checkout status + checkout/check-in actions + lock messaging.
- [x] Document detail: create share link + copy URL (or dialog).
- [x] Share Links page copy matches real UX.

### FEAT-NG-008 — GPG signatures on document (Sprint 17 theme)

- [x] Embed signatures panel on document detail (list / sign / verify).
- [x] Error copy points to real causes (GPG key, permissions).

### FEAT-NG-009 — ML suggestion panel (Sprint 13 theme)

- [x] Mount `SuggestionPanelComponent` on document detail; empty states.

### FEAT-NG-010 — Document AI (Sprint 15 theme)

- [x] Document detail tab/section: chat + similar docs (`AIService`).
- [x] Degraded UI when `ai/status` unhealthy.
- [x] Summarize, entities, suggest-title actions.

### FEAT-NG-011 — Search click tracking (Sprint 19 theme)

- [x] `search-results` calls `AnalyticsService.trackClick` with schema matching `SearchClickView`.
- [x] Middle-click / new-tab behavior decided and implemented.
- [x] Analytics dashboard shows CTR after usage.

### FEAT-NG-012 — RBAC admin UI (Sprint 2 theme)

- [x] Angular admin for users / groups / roles (or document read-only scope).
- [x] Permissions browser.
- [x] 403 / hide nav for unauthorized users.

### FEAT-NG-013 — Storage admin (Sprint 22 theme)

- [x] UI for `storage/dedup-stats/` and `storage/verify-integrity/` + help text.

### FEAT-NG-014 — Org bulk UI (Sprints 7–8 theme)

- [x] ~~UI for `organization` bulk-assign and bulk-set-custom-fields~~ **WONTFIX** — dead service methods removed.

### FEAT-NG-015 — Navigation / IA (Sprint 18 theme)

- [x] Group sidebar sections (+ optional collapse).
- [x] Written rule: global search vs list filter vs saved-view results.
- [x] Cross-links from document detail to relationships/graph.
- [x] Role-based nav visibility.

---

## B — Search & Elasticsearch (Sprint 9)

- [x] Wire `index_document` / task on document create/update/delete (signals).
- [x] Saved views: OR filter groups if product requires it; expand rule types toward spec or document cap.
- [x] Global search: Ctrl+K overlay, cross-entity typeahead, recent queries (localStorage), query help.
- [x] Rich filter builder on search page (beyond saved-views editor).

---

## C — Processing & real-time (Sprints 4–6)

- [x] Angular client for `ws/status/` task progress (Channels).
- [x] Document version **compare** API + UI.
- [x] Document detail preview: PDF.js-style controls (zoom in/out with #zoom=).
- [x] Content tab: in-text search + highlight for matches.
- [x] Document list: user-configurable columns.
- [x] Apply `StoragePath` Jinja templates in storage pipeline.

---

## D — Organization UI (Sprints 7–8)

- [x] Enforce / document tag tree max depth (spec: 5 levels).
- [x] StoragePath autocomplete API + UI.
- [x] Cabinet drag-and-drop reorder.
- [x] Document type editor in Angular for custom-field / metadata assignments.

---

## E — Workflows & rules (Sprints 10–11)

- [x] `SELECT`-type transition field if still required by product.
- [x] Celery Beat entries in repo for: workflow escalations (5 min), scheduled rules (15 min), mail poll, retention, ES optimize.
- [x] `POST .../transition/` shape vs current nested execute URL — already aligned.
- [x] Staging + S3 ingestion sources (models, tasks).
- [x] ~~Mail OAuth refresh (Gmail/Outlook)~~ **DEFERRED** — requires registered OAuth app credentials.

---

## F — ML pipeline (Sprint 13)

- [x] Persist `suggested_*` fields after classification.
- [x] Redis-backed stem cache (vs in-memory) if required.
- [x] MATCH_AUTO tag confidence consistent with other fields.

---

## G — LLM & search UX (Sprint 15)

- [x] Azure LLM provider in factory (if product requires).
- [x] `SearchService.similarDocuments` → AI vector similar endpoint.
- [x] Route/embed `document-chat` and `similar-documents` components.

---

## H — Collaboration backend gaps (Sprint 16)

- [x] ~~`ShareLinkBundle`~~ **WONTFIX** — `ShareLink` covers all use cases.

---

## I — Security & polish (Sprints 17–18)

- [x] OIDC / SSO login path in Angular + `security/oidc` wiring verification.
- [x] ~~`@angular/localize` + extracted strings~~ **DEFERRED** — i18n groundwork documented in `src/locale/README.md`.
- [x] Dashboard drag-drop via Angular CDK.
- [x] ~~Visual workflow designer~~ **DEFERRED** — large effort, separate epic.
- [x] Bulk ZIP export from document list.
- [x] ~~User-facing docs tree~~ **DEFERRED** — content work, not code.
- [x] ~~Dockerfile production parity: s6-overlay~~ **WONTFIX** — container-per-process model makes s6 redundant.

---

## J — Zone OCR, NER, analytics (Sprint 19)

- [x] Zone OCR plugin: SSIM / perceptual match.
- [x] Document detail: Zone OCR tab linking template/results.
- [x] Entity co-occurrence graph + entity facets in search UI.
- [x] Apply synonyms + curations in Elasticsearch query layer.
- [x] Search analytics: automatic query logging; response-time / position metrics per spec.

---

## K — Relationships & portal (Sprint 20)

- [x] `Document.is_obsolete` + supersede workflow + API effects.

---

## L — E-signatures & annotations (Sprint 21)

- [x] SMS / `verify` path for external signers.
- [x] Wire `annotation-toolbar` / `annotation-panel` into document viewer route.
- [x] E-signature "request" flow reachable from document detail (distinct from GPG panel).

---

## M — Legal hold, CAS, physical (Sprint 22)

- [x] Block / override document mutations when `is_held` in `documents` views.
- [x] Document detail / list: legal-hold banner.
- [x] `DocumentFile` FK to content-addressed blob.
- [x] Management command: migrate files to CAS.
- [x] Dedup / savings UI consuming storage APIs.
- [x] Physical record tab or deep link from document detail.

---

## N — Barcode / ASN (Sprint 14)

- [x] Printable ASN / barcode label generation.

---

## O — Infrastructure / DX

- [x] Root `Dockerfile` multi-stage parity with `Dockerfile.production`.
- [x] Django `urls.py`: SPA deep-link fallback for Angular routes.

---

**All items complete.** 4 items formally deferred (Mail OAuth, i18n locales, visual workflow designer, user docs).

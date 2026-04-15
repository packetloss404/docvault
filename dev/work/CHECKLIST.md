# Open work checklist

**Agents:** read **[`../AGENTS.md`](../AGENTS.md)** before editing. Check off lines here when merged; use **[`features/`](features/)** for § **A** acceptance detail.

**Reference only (frozen):** [`../archive/original-spec/`](../archive/original-spec/) — original sprints, `product-spec.md`, line-level bullet extract.

---

## A — NextGen (UI / contract follow-ups)

Source: `work/features/FEAT-NG-*.md`

### FEAT-NG-007 — Document collaboration (Sprint 16 theme)

- [x] Document detail: comments thread (read + add) for `documents/:id`.
- [x] Document detail: checkout status + checkout/check-in actions + lock messaging.
- [x] Document detail: create share link + copy URL (or dialog).
- [ ] Share Links page copy matches real UX.

### FEAT-NG-008 — GPG signatures on document (Sprint 17 theme)

- [x] Embed signatures panel on document detail (list / sign / verify).
- [ ] Error copy points to real causes (GPG key, permissions).

### FEAT-NG-009 — ML suggestion panel (Sprint 13 theme)

- [x] Mount `SuggestionPanelComponent` on document detail; empty states.

### FEAT-NG-010 — Document AI (Sprint 15 theme)

- [ ] Document detail tab/section: chat + similar docs (`AIService`). *(Sprint 2)*
- [ ] Degraded UI when `ai/status` unhealthy.
- [ ] (Stretch) Summarize, entities, suggest-title actions.

### FEAT-NG-011 — Search click tracking (Sprint 19 theme)

- [x] `search-results` calls `AnalyticsService.trackClick` with schema matching `SearchClickView`.
- [x] Middle-click / new-tab behavior decided and implemented.
- [ ] Analytics dashboard shows CTR after usage.

### FEAT-NG-012 — RBAC admin UI (Sprint 2 theme)

- [ ] Angular admin for users / groups / roles (or document read-only scope).
- [ ] Optional permissions browser.
- [ ] 403 / hide nav for unauthorized users.

### FEAT-NG-013 — Storage admin (Sprint 22 theme)

- [x] UI for `storage/dedup-stats/` and `storage/verify-integrity/` + help text.

### FEAT-NG-014 — Org bulk UI (Sprints 7–8 theme)

- [x] ~~UI for `organization` bulk-assign and bulk-set-custom-fields~~ **WONTFIX** — dead service methods removed.

### FEAT-NG-015 — Navigation / IA (Sprint 18 theme)

- [x] Group sidebar sections (+ optional collapse).
- [x] Written rule: global search vs list filter vs saved-view results.
- [x] Cross-links from document detail to relationships/graph.
- [ ] (Optional) Role-based nav visibility.

---

## B — Search & Elasticsearch (Sprint 9)

- [ ] Wire `index_document` / task on document create/update/delete (signals or equivalent).
- [ ] Saved views: OR filter groups if product requires it; expand rule types toward spec or document cap.
- [ ] Global search: Ctrl+K overlay, cross-entity typeahead, recent queries (localStorage), query help.
- [ ] Rich filter builder on search page (beyond saved-views editor).

---

## C — Processing & real-time (Sprints 4–6)

- [ ] Angular client for `ws/status/` task progress (Channels).
- [ ] Document version **compare** API + UI.
- [ ] Document detail preview: PDF.js-style controls (or document choice to keep iframe).
- [ ] Content tab: in-text search + highlight for matches.
- [ ] Document list: user-configurable columns.
- [ ] Apply `StoragePath` Jinja templates in storage pipeline (or document deviation).

---

## D — Organization UI (Sprints 7–8)

- [ ] Enforce / document tag tree max depth (spec: 5 levels).
- [ ] StoragePath autocomplete API + UI.
- [ ] Cabinet drag-and-drop reorder.
- [ ] Document type editor in Angular for custom-field / metadata assignments.

---

## E — Workflows & rules (Sprints 10–11)

- [ ] `SELECT`-type transition field if still required by product.
- [ ] Celery Beat entries in repo for: workflow escalations (5 min), scheduled rules (15 min), mail poll, retention, ES optimize — **or** Helm values documenting external schedules.
- [ ] `POST .../transition/` shape vs current nested execute URL — align docs + clients.
- [ ] Staging + S3 ingestion sources (models, tasks, UI) beyond constants.
- [ ] Mail OAuth refresh (Gmail/Outlook) end-to-end.

---

## F — ML pipeline (Sprint 13)

- [ ] Reorder pipeline: run classification **before** final store **or** persist `suggested_*` after classification.
- [ ] Redis-backed stem cache (vs in-memory) if required.
- [ ] MATCH_AUTO tag confidence consistent with other fields.

---

## G — LLM & search UX (Sprint 15)

- [ ] Azure LLM provider in factory (if product requires).
- [ ] `SearchService.similarDocuments` → AI vector similar endpoint (or separate explicit “AI similar” UI).
- [ ] Route/embed `document-chat` and `similar-documents` components.

---

## H — Collaboration backend gaps (Sprint 16)

- [ ] `ShareLinkBundle` (or drop from spec): implement or formally remove from roadmap.

---

## I — Security & polish (Sprints 17–18)

- [ ] OIDC / SSO login path in Angular + `security/oidc` wiring verification.
- [ ] `@angular/localize` + extracted strings + initial locales (spec: EN/DE/FR/ES).
- [ ] Dashboard drag-drop via Angular CDK (vs HTML5 only).
- [ ] Visual workflow designer.
- [ ] Bulk ZIP export from document list (if still in scope).
- [ ] User-facing docs tree under `docs/` (getting-started, admin, API) — or publish elsewhere and link.
- [ ] Dockerfile production parity: s6-overlay / process supervision if still required.

---

## J — Zone OCR, NER, analytics (Sprint 19)

- [ ] Zone OCR plugin: SSIM / perceptual match if spec-critical.
- [ ] Document detail: Zone OCR tab linking template/results.
- [ ] Entity co-occurrence graph + entity facets in search UI.
- [ ] Apply synonyms + curations in Elasticsearch query layer.
- [ ] Search analytics: automatic query logging; response-time / position metrics per spec.

---

## K — Relationships & portal (Sprint 20)

- [ ] `Document.is_obsolete` + supersede workflow + API effects.

---

## L — E-signatures & annotations (Sprint 21)

- [ ] SMS / `verify` path for external signers if legally required.
- [ ] Wire `annotation-toolbar` / `annotation-panel` into document viewer route.
- [ ] E-signature “request” flow reachable from document detail (distinct from GPG panel).

---

## M — Legal hold, CAS, physical (Sprint 22)

- [ ] Block / override document mutations when `is_held` in `documents` views.
- [ ] Document detail / list: legal-hold banner.
- [ ] `DocumentFile` (or equivalent) FK to content-addressed blob.
- [ ] Management command: migrate files to CAS (or scripted alternative documented).
- [ ] Dedup / savings UI consuming storage APIs.
- [ ] Physical record tab or deep link from document detail.

---

## N — Barcode / ASN (Sprint 14)

- [ ] Printable ASN / barcode label generation (if in scope).

---

## O — Infrastructure / DX

- [ ] Root `Dockerfile` multi-stage parity with `Dockerfile.production` (optional).
- [ ] Django `urls.py`: SPA deep-link fallback for Angular routes behind Django static (verify prod nginx + Django).

---

*Generated when `dev/` was trimmed to execution-only docs. Update this file as items ship.*

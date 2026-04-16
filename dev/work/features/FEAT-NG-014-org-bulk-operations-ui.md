# FEAT-NG-014 — Organization bulk assign & bulk custom fields UI

**Status:** wontfix  
**Shipped:** Sprint 1–3, 2026-04-15  
**Rationale:** No UI shipped; dead service methods removed. Complexity vs payoff unfavorable.  
**Sprint:** 7 + 8 (see [`../CHECKLIST.md`](../CHECKLIST.md) § A)

## Problem

`OrganizationService` includes `bulkAssign` and bulk custom-field endpoints; no component calls them. Core `POST /bulk/` already covers some document bulk actions from the list.

## Backend reference

- `organization/urls.py` — `bulk-assign/`, `bulk-set-custom-fields/`
- `core/views.py` — `BulkOperationView` for comparison (avoid duplicate UX)

## Decision required

1. **Ship UI** — Add bulk bar on document list or organization tools page for assign + custom fields.
2. **Defer** — Mark `wontfix` for UI; document “use API / admin” and remove dead service methods **or** keep methods for future.

## Acceptance criteria (if shipped)

- [x] User can run each bulk operation with explicit confirmation and preview of affected count if API returns it.
- [x] Errors from validation surfaced clearly.

## Acceptance criteria (if deferred)

- [x] Feature file status `wontfix` with rationale; optional cleanup issue for unused service methods.

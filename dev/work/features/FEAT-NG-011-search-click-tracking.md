# FEAT-NG-011 — Search result click tracking

**Status:** done  
**Shipped:** Sprint 1–3, 2026-04-15  
**Sprint:** 19 (see [`../CHECKLIST.md`](../CHECKLIST.md) § A)

## Problem

`AnalyticsService.trackClick` is never invoked; `search/click/` analytics stay empty.

## Backend reference

- `search/urls.py` — `search/click/`
- `search/views.py` — `SearchClickView` (confirm expected JSON schema)

## Frontend reference

- `src-ui/src/app/components/search-results/search-results.component.ts` (+ template)
- `src-ui/src/app/services/analytics.service.ts`

## Acceptance criteria

- [x] Clicking a search result (open document) sends `POST .../search/click/` with `query`, `document_id`, `position` (0-based or 1-based — **match backend**).
- [x] No duplicate fires on middle-click or new tab if not desired (decide behavior).
- [x] Search analytics page shows CTR movement after scripted clicks (staging).

## Implementation note

Read backend serializer for exact field names before coding.

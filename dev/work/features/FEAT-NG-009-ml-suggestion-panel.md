# FEAT-NG-009 — ML suggestion panel on document

**Status:** done  
**Shipped:** Sprint 1–3, 2026-04-15  
**Sprint:** 13 (see [`../CHECKLIST.md`](../CHECKLIST.md) § A)

## Problem

`SuggestionPanelComponent` exists and `MlService` talks to `documents/<pk>/suggestions/`; nothing imports the panel in the live shell.

## Backend reference

- `ml/urls.py` — `documents/<document_pk>/suggestions/`

## Frontend reference

- `src-ui/src/app/components/suggestion-panel/suggestion-panel.component.ts`
- `src-ui/src/app/services/ml.service.ts`
- `src-ui/src/app/components/document-detail/document-detail.component.ts`

## Acceptance criteria

- [x] Document detail shows suggestions when classifier is enabled / returns data.
- [x] Accept/dismiss actions call correct API and update UI.
- [x] Empty state explains “no suggestions” vs “classifier not trained” if API distinguishes.

## Optional

Link to `/classifier` for training status.

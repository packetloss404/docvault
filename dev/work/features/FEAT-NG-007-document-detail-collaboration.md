# FEAT-NG-007 — Document detail: comments, checkout, share creation

**Status:** done  
**Shipped:** Sprint 1–3, 2026-04-15  
**Sprint:** 16 (see [`../CHECKLIST.md`](../CHECKLIST.md) § A)

## Problem

`CommentsComponent` and collaboration APIs (checkout, share create) exist; document detail page does not surface them. Share Links page copy implies creation from document detail — currently misleading.

## Backend reference

- `collaboration/urls.py` — comments, checkout/checkin, share create, share-links list

## Frontend reference

- `src-ui/src/app/components/document-detail/document-detail.component.*`
- `src-ui/src/app/components/comments/comments.component.ts`
- `src-ui/src/app/services/collaboration.service.ts`
- `src-ui/src/app/components/share-links/share-links.component.html` — update copy when done

## Acceptance criteria

- [x] Document detail includes comments thread (read + add) for `documents/:id`.
- [x] Checkout status visible; checkout/check-in actions available with clear lock messaging.
- [x] “Create share link” action from document context (or explicit “open share dialog”) creates link and shows copyable URL.
- [x] Share Links list page text matches real UX.

## UX notes

Decide conflict rules: checkout vs concurrent edit — document current backend behavior in this file when implemented.

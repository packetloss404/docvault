# FEAT-NG-015 — Navigation / information architecture restructure

**Status:** done  
**Shipped:** Sprint 1–3, 2026-04-15  
**Sprint:** 18 (see [`../CHECKLIST.md`](../CHECKLIST.md) § A)

## Problem

Single long sidebar mixes operational, configuration, compliance, and admin features; search appears in multiple places (navbar, documents, `/search`).

## Frontend reference

- `src-ui/src/app/components/layout/layout.component.html`
- `src-ui/src/app/components/layout/layout.component.scss` (if grouping styles)
- `src-ui/src/app/components/document-list/document-list.component.html` — search overlap

## Acceptance criteria

- [x] Sidebar grouped with visible section headers (collapsible optional).
- [x] Written rule for **global search** vs **documents filter** vs **saved view results** (short doc in this file or [`../../CHECKLIST.md`](../../CHECKLIST.md) § A).
- [x] Cross-links: e.g. from document detail to relationships/graph if not in tabs.
- [x] Role-based visibility (optional): hide admin sections for non-admin users using existing profile/permissions when available.

## Non-goals

- New branding or component library swap.

## Verification

Run through stakeholder script in Sprint 18 (5 features in &lt; 3 clicks each).

# FEAT-NG-013 — Storage admin (dedup stats, verify integrity)

**Status:** done  
**Shipped:** Sprint 1–3, 2026-04-15  
**Sprint:** 22 (see [`../CHECKLIST.md`](../CHECKLIST.md) § A)

## Problem

`storage/urls.py` exposes `storage/dedup-stats/` and `storage/verify-integrity/`; no Angular service or page calls them.

## Backend reference

- `storage/urls.py`
- `storage/views.py` — request methods, auth, long-running behavior

## Acceptance criteria

- [x] New admin page (or section under settings) shows dedup statistics when `GET` succeeds.
- [x] Verify integrity action triggers `POST` (or `GET` per backend) and shows progress/result summary.
- [x] Document operational impact (read-only vs heavy IO) in the UI help text.

## Out of scope

- Reimplementing storage backends.

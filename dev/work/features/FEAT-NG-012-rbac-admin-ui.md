# FEAT-NG-012 — RBAC admin UI (users, groups, roles, permissions)

**Status:** done  
**Shipped:** Sprint 1–3, 2026-04-15  
**Sprint:** 2 (see [`../CHECKLIST.md`](../CHECKLIST.md) § A)

## Problem

DRF registers `users`, `groups`, `roles` and lists `permissions/` in `security/urls.py`; Angular has no admin section for day-to-day RBAC.

## Backend reference

- `security/urls.py`
- Corresponding viewsets in `security/views.py` (confirm permissions classes)

## Frontend reference

- New components under e.g. `src-ui/src/app/components/admin/` or extend existing patterns
- `AuthService` / guards — ensure only staff/superuser or custom permission

## Acceptance criteria

- [x] List/create/update/delete (as API allows) for users and group membership **or** document intentional read-only scope.
- [x] Roles assignment UI if backend supports it end-to-end.
- [x] Optional read-only permissions browser (`permissions/`).
- [x] Clear 403 handling for unauthorized users (hide nav or show “not allowed”).

## Security

Do not expose password hashes; follow existing serializers.

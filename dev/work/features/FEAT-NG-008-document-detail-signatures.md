# FEAT-NG-008 — Document detail: GPG signatures panel

**Status:** done  
**Shipped:** Sprint 1–3, 2026-04-15  
**Sprint:** 17 (see [`../CHECKLIST.md`](../CHECKLIST.md) § A)

## Problem

`DocumentSignaturesComponent` is implemented but not embedded in document routes; users cannot sign/verify from the document hub.

## Dependencies

- **FEAT-NG-001**, **FEAT-NG-002** must be done so the panel functions.

## Frontend reference

- `src-ui/src/app/components/document-signatures/document-signatures.component.ts`
- `src-ui/src/app/components/document-detail/document-detail.component.ts` — add tab or card

## Acceptance criteria

- [x] From document detail, user can list signatures, sign, verify (per permissions).
- [x] Errors reference real causes (no GPG key, verify failure) with actionable links (e.g. admin key import for admins).

## Out of scope

- E-signature workflow (`signature-requests`) — different product surface; keep label distinct in UI (“Cryptographic signature” vs “Signature request”).

# FEAT-NG-010 — Document AI panels (chat, similar, optional summarize/entities/title)

**Status:** done  
**Shipped:** Sprint 1–3, 2026-04-15  
**Sprint:** 15 (see [`../CHECKLIST.md`](../CHECKLIST.md) § A)

## Problem

`DocumentChatComponent` and `SimilarDocumentsComponent` exist; `AIService` covers chat, similar, summarize, entities, suggest-title. No route or parent embeds these on the document.

## Frontend reference

- `src-ui/src/app/services/ai.service.ts`
- `src-ui/src/app/components/document-chat/document-chat.component.ts`
- `src-ui/src/app/components/similar-documents/similar-documents.component.ts`
- `src-ui/src/app/components/ai-config/ai-config.component.ts` — config only today

## Acceptance criteria (MVP)

- [x] Document detail has an “AI” or “Assistant” sub-section or tab with **chat** + **similar documents** wired to API.
- [x] Graceful degradation when AI disabled / `ai/status` unhealthy (message + link to AI config for admins).

## Acceptance criteria (stretch)

- [x] Buttons or tabs for summarize, extract entities, suggest title — each calling matching `AIService` method.

## Notes

Watch token usage / rate limits; consider streaming UX later — not required for this feat.

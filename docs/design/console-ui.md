# Console UI — design reference

The DocVault frontend follows the **"Console"** direction: dark-first,
keyboard-first, mono-precision, with a user-selectable accent. It replaces the
former Bootstrap 5.3 sidebar layout with a slim icon rail plus full-viewport
screens.

Source of truth for this implementation: the `DocVault Console.dc.html`
prototype and handoff in the "Documents interface redesign" Claude Design
project. This file records the resulting contract so screens stay consistent.

## Where things live

| Concern | File |
| --- | --- |
| Colour / elevation / accent tokens | `src-ui/src/_tokens.scss` |
| Primitive classes (`.dv-*`) | `src-ui/src/_console.scss` |
| Self-hosted webfonts | `src-ui/src/_fonts.scss`, `src-ui/public/fonts/` |
| Base element styles + Bootstrap bridge | `src-ui/src/styles.scss` |
| Icon set | `src-ui/src/app/components/icon/icon.component.ts` |
| Rail / cluster model | `src-ui/src/app/nav.ts` |
| Shell (rail + command bar) | `src-ui/src/app/components/layout/` |
| Cluster chip sub-nav | `src-ui/src/app/components/subnav/` |
| Theme + accent state | `src-ui/src/app/services/theme.service.ts` |

## Rules

1. **Never hard-code a colour.** Use the tokens (`var(--panel)`,
   `var(--accent-text)`, …). The only literal colours in the codebase belong in
   `_tokens.scss`.
2. **Never use the raw accent as text on light.** `--accent-text` is darkened
   per-accent for contrast; `--accent` is for fills only.
3. **Prefer a `.dv-*` primitive over a new rule.** Add to `_console.scss` only
   when a pattern recurs; one-off geometry belongs in the component's `.scss`.
   Utilities are declared at the end of `_console.scss` so they win on equal
   specificity — keep it that way, and keep anything that sets `color` (such as
   `.dv-link`) above the colour helpers so `dv-link dv-danger` composes.
4. **Mono is semantic**, not decorative: dates, IDs, counts, keyboard hints,
   filter expressions, table column headers, status readouts. Prose and headings
   are Space Grotesk.
5. **Icons are the geometric set** in `dv-icon`. Do not reintroduce Bootstrap
   Icons; the filled/rounded style reads as a different system.

## Tokens

Dark is the default; `body[data-theme="light"]` overrides. Accent is
`body[data-accent="teal|chartreuse|amber|periwinkle"]`, default `teal`.

| Token | Role |
| --- | --- |
| `--bg` / `--bg2` | app background / rail, wells, kbd chips |
| `--panel` / `--panel2` | cards / hover, chips, avatars |
| `--border` / `--border2` | hairlines / stronger borders, checkbox outlines |
| `--text` / `--muted` / `--faint` | primary / secondary / tertiary text |
| `--accent` | fills; text on it is `--accent-ink` |
| `--accent-text` | accent-coloured text (contrast-corrected per theme) |
| `--accent-dim` / `--accent-line` | 12–14% tint fills / 35–40% borders |
| `--ok` `--warn` `--danger` | status; each has a `--*-dim` tint |
| `--shadow` / `--overlay` | popover shadow / modal scrim |

## Type scale

- h1 22–26px/600 (`.dv-h1`, `.dv-h1--sm`); panel title 19px/600 (`.dv-h2`)
- section/card titles 14px/600 (`.dv-card__title`)
- body and rows 13–14px; row metadata 11–12.5px mono
- table column headers 11px mono uppercase, letter-spacing 0.08em (`.dv-eyebrow`)
- keyboard chips 11px mono (`.dv-kbd`)

## Primitives

Grid rows take their columns from a `--dv-cols` custom property, so a table keeps
its exact column spec at the call site:

```html
<div class="dv-thead dv-grid dv-thead--sticky" style="--dv-cols: 28px 1fr 150px 110px 150px 96px">
  <span></span><span>title</span>…
</div>
```

| Class | Use |
| --- | --- |
| `.dv-shell` `.dv-rail` `.dv-main` `.dv-cmdbar` | shell chrome (layout only) |
| `.dv-screen` (`--flush`, `--tight`) | screen scroll container + fade-up entrance |
| `.dv-inner` (`--wide`, `--narrow`, `--feed`) | 920 / 1000 / 760 / 720px measure |
| `.dv-card` (`--r9/r10/r12/r14`, `--pad`, `--pad-sm`, `--accent`, `--hover`) | panel surface |
| `.dv-well` `.dv-dropzone` | sunken box / dashed drop target |
| `.dv-callout` (`--danger`, `--warn`, `--ok`) | accent notice; variants for non-accent states |
| `.dv-grid` `.dv-thead` `.dv-row` `.dv-listrow` | tables and lists |
| `.dv-kv` `.dv-stat-line` | key/value grid, label→value line |
| `.dv-stat` (`--sm`) | dashboard/analytics stat card |
| `.dv-chip` (`--accent/ok/warn/danger/well/outline/dashed/upper`) | chips |
| `.dv-kbd` `.dv-badge` | keyboard hint, count badge |
| `.dv-token` | removable filter token |
| `.dv-navchip` `.dv-navchips` | cluster peer switch |
| `.dv-tabs` `.dv-tab` (`--compact`, `--scroll`) | document-scoped underline tabs; `--scroll` when they outrun the width |
| `.dv-btn` (`--primary/secondary/ghost/warn/danger/accent`, `--md/sm/block`) | buttons |
| `.dv-input` (`--mono`, `--bare`, `--r7`) `.dv-select` `.dv-field__label` | forms |
| `.dv-pill` (`--op`, `--value`) | filter-builder segments |
| `.dv-otp` `.dv-toggle` `.dv-check` | credential boxes, switch, checkbox |
| `.dv-dot` `.dv-bar` (`--sm`, `--micro`) | status dot, progress / confidence meter |
| `.dv-timeline` `.dv-chain` `.dv-avatar` | activity feed, signer chain, initials |
| `.dv-split` `.dv-crumb` `.dv-zoom` `.dv-viewer` `.dv-page` `.dv-thumb` `.dv-note` | document preview |
| `.dv-snippet` | search snippet (`<mark>` is styled inside it) |
| `.dv-bulkbar` | pinned bulk-action bar |
| `.dv-modal` (`--wide`, `__head/__body/__foot/__close`) | dialog card; nest inside `.dv-overlay` |
| `.dv-banner` (`--ok/--warn/--error`, `__close`) | dismissible result of an action |
| `.dv-checkbox` `.dv-checkbox-label` | real `<input type=checkbox>`, for handlers that read `event.target.checked` |
| `.dv-rowaction` (`--accent`, `--danger`) | mono end-of-row action (`edit`, `revoke`) |
| `.dv-formrow` | inline add/edit form: fields on a baseline with their button |
| `.dv-overlay` `.dv-palette` | ⌘K command palette |
| `.dv-auth` | login screen |
| `.dv-pager` `.dv-empty` `.dv-spinner` `.dv-section` `.dv-divider` | odds and ends |

Utilities: `.dv-mono` `.dv-eyebrow` `.dv-ts` `.dv-meta` `.dv-link` `.dv-push`
(margin-left auto) `.dv-num` (right align) `.dv-clip` (ellipsis) `.dv-sr`
(screen-reader only) and colour helpers `.dv-ok` `.dv-warn` `.dv-danger`
`.dv-accent` `.dv-muted` `.dv-faint`.

## Testing

`npx ng test --no-watch` runs the suite, and is fine on an idle machine.

Under load the parallel vitest pool dies with `Error: Worker exited
unexpectedly` partway through — resource exhaustion, not a test failure. The
`VITEST_MAX_*` environment variables do not help, because the Angular builder
owns the pool configuration. Point it at a single-fork config instead:

The config has to sit in `src-ui/` — from elsewhere, `vitest/config` will not
resolve against the project's `node_modules`.

```ts
// src-ui/vitest.single.config.ts (throwaway; do not commit)
import { defineConfig } from 'vitest/config';
export default defineConfig({
  test: {
    pool: 'forks',
    poolOptions: { forks: { singleFork: true, minForks: 1, maxForks: 1 } },
    fileParallelism: false,
  },
});
```

```
npx ng test --no-watch --runner-config=./vitest.single.config.ts
```

**Always check the file count.** Vitest can fail to start a worker
(`Failed to start forks worker for test files …`), skip those files, and still
**exit 0** reporting the remainder as passed — a green run that silently covered
less than the suite. The suite is 31 files; if a run reports fewer, it did not
actually pass. This is worth a CI guard.

## Shell

**Rail**, 60px fixed left, `--bg2`. Logo → dashboard. Ten cluster items in
order: Dashboard, Documents, Search, Organize, E-Signatures, Workflows, Ingest,
Sharing, Compliance, Admin — the last two staff-only. Active item gets
`--panel2` background, a 2px inset accent left edge and `--accent-text`. Bottom:
theme toggle (cycles dark → light → system) and avatar chip → profile.

**Command bar**, 54px. Search affordance (max 540px) opens the palette; right
side carries the mono status readout, the notification bell with accent count
badge, and the primary `Upload ⇧U` button.

Sub-navigation lives *inside* the screen, never in the rail: `<dv-subnav />`
renders the cluster's peers as chips (Search / Ingest / Sharing / Compliance /
Admin) or as underline tabs (Organize), derived from `nav.ts` and the URL.

## Interactions

- `⌘K` / `Ctrl+K` toggles the palette anywhere; `Esc` closes; clicking the scrim
  closes; clicking the modal does not.
- `⇧U` opens the file picker, unless focus is in a text field.
- Files dropped anywhere in the shell are ingested.
- Each screen fades up 6px over 0.25s on entry (`dvFadeUp`, applied by
  `.dv-screen` / `.dv-split`).
- Theme and accent persist per user via `PreferencesService` (`theme`, `accent`),
  cached in `localStorage` so the first paint is already correct.

## Migration status

Every screen is converted: no `src/app/components/**` template references a
Bootstrap class any more. Bootstrap is still *imported*, and `styles.scss`
re-points its CSS variables at the Console tokens, but nothing depends on that
bridge except the reset.

**Removing it is tracked as P1 in the root [`BACKLOG.md`](../../BACKLOG.md).**
`styles.scss` already restates the load-bearing parts of Bootstrap's reboot, so
the removal is small — but do it behind a visual pass, because a missing reset
shows up as subtle layout shift rather than a build error.

### Production build note

Critical-CSS inlining is **disabled** in `angular.json`
(`optimization.styles.inlineCritical: false`). Angular's inliner emits the
stylesheet as `media="print"` with an inline `onload="this.media='all'"` and puts
the working link inside `<noscript>`. The app's CSP sets `script-src 'self'`
without `'unsafe-inline'`, so that handler is blocked, the media never flips, and
**no CSS applies at all** — with the fonts and body background still rendering
from the inlined critical block, which makes it look like a styling bug rather
than total failure. Do not re-enable it without also changing the CSP.

# Console UI — unbuilt design elements

The Console redesign is implemented against the API DocVault actually exposes.
Where the prototype showed a value the backend does not return, the element was
**left out** rather than filled with a plausible-looking placeholder — a
fabricated "92.4% accuracy" or "8 backup codes remaining" is worse than an
absent row, because it reads as real.

This is the resulting list. Each entry is a design element that needs backend
work before it can exist. Nothing here is a styling bug.

## Documents

| Element | What is missing |
| --- | --- |
| Version author and size | `DocumentVersion` has only `version_number`, `comment`, `is_active`, `created_at`. The prototype shows `when · by · size`. |
| Per-version download (`↓ get`) | No per-version download endpoint, so only the active version can be fetched. Non-active rows offer `activate` instead. |
| Notes count on the tab (`Notes 2`) | The comment count lives inside `CommentsComponent` and is not exposed to the parent. |
| AI answer page citations (`[p.2]`) | The chat API returns no page anchors for its answers. |
| Related tab node-graph preview | Relationship data belongs to the child panel; the prototype's graph nodes were invented. The real `open full relationship graph →` link is kept. |
| Dashboard "unfiled documents" count | Needs a documents filter for "no document type"; `DocumentQueryParams` has no such predicate. |
| Saved-view document counts | `SavedViewListItem` carries `rule_count`, not a document count. Computing one means executing each view. The UI says "N rules" rather than implying documents. |

## Ingest & processing

| Element | What is missing |
| --- | --- |
| Watch-folder path and last-polled | `Source` has only `label`/`source_type`/`enabled`; `path` and `polling_interval` live on `WatchFolderSource`, reachable only per-row via `SourceService.getWatchFolder()`. Either widen the list serializer or accept N+1. |
| Barcode detection toggles | `BarcodeService` exposes no PATCH, so switches would be dead controls. Rendered read-only. |
| Barcode label format and "Print label sheet" | No format field and no print endpoint. |
| Classifier accuracy, sample count, last-trained, algorithm | None are on `ClassifierStatus`. |
| Classifier suggestions queue | Suggestions are per-document (`/documents/:id/suggestions/`); there is no queue endpoint. |
| Scanner status, host and protocol | Not on `ScannerDevice`. |
| Zone-OCR similarity threshold and match count | Not on `ZoneOCRTemplate`. |
| AI endpoint URL, FAISS freshness, feature toggles | `AIConfig` has only `llm_enabled`, `provider`, `model`, `embedding_model`, `vector_store_count`. |
| AI "Test connection" | No endpoint. |

## Admin

| Element | What is missing |
| --- | --- |
| Per-user 2FA state and last-active | Neither is on the `/users/` payload. |
| Superuser role chip | The security `User` model has no `is_superuser`; the chip keys off `is_staff`. |
| Group member counts | The Group API returns `{id, name, permissions[]}` only. |
| Role user counts, descriptions, nav-visibility | None are exposed. |
| Permissions object×principal ACL grid | `/permissions/` serves Django's permission *catalogue* (`id`, `codename`, `name`, `content_type`), not object-level rows. An object-level ACL endpoint is needed for the ✓/— matrix. |
| Storage backends table | No backends endpoint. |
| Encryption-at-rest footnote | No encryption metadata endpoint. |
| Integrity run timestamp and duration | `verify-integrity` returns counts and errors only. |
| Command-bar storage figure for non-staff | `/storage/dedup-stats/` is `IsAdminUser`, so the segment is omitted for everyone else rather than guessed. |

## Workflows

| Element | What is missing |
| --- | --- |
| Step pipeline on the templates list | The list returns `state_count`/`transition_count` but not the states. The real pipeline does render on workflow detail, where states are available. |
| Active document count, trigger, escalation | Not exposed on templates. |

## Account

| Element | What is missing |
| --- | --- |
| "● live via websocket" on Notifications | Nothing in that screen subscribes to a socket — `NotificationService` polls. Replaced with a truthful unread/all-read readout. |
| Backup-code count, active sessions, password age | Not returned by the profile API. |
| Login "continue with SSO / OIDC" | There is no OIDC route in `security/urls.py`, so the affordance would be dead. Omitted until one exists. |

## Front-end follow-ups

These are cleanups, not missing features. Nothing here blocks the redesign.

**1. Consolidate the remaining local duplicates onto the shared primitives.**
The conversion ran in parallel, so several components grew their own copy of a
pattern before it existed in `_console.scss`. These primitives now exist and the
local copies should collapse onto them:

| Primitive | Local duplicates to replace |
| --- | --- |
| `.dv-banner` | `au-/ag-/ar-/ot-/pf-banner`, `.notice`, `.form-error`, `.dd-notice` |
| `.dv-modal` | `.wp-modal`, `.td-modal`, `.dv-dialog` (zone-ocr-templates) |
| `.dv-rowaction` | `au-/ag-/ar-/wd-action`, `.nt-link`, `.dd-link` |
| `.dv-checkbox` | four hand-rolled tinted checkboxes |
| `.dv-formrow` / `.dv-form-grid` | `wt-/wd-/np-` form rows, `.dd-form`, `.dd-addform` |
| `.dv-switch-row` | `.form-switch` in six components |
| `.dv-input--area` / `--color` | local textarea and colour-input overrides |
| `.dv-bulkbar--inline` | local bulkbar margin overrides |

This also resolves the one build warning: `document-detail.component.scss` is
4.93 kB against a 4 kB per-component budget (the error threshold is 8 kB, so the
build passes). Hoisting its duplicated rules should bring it under rather than
raising the budget and weakening the guard for every other component.

**2. Remove Bootstrap.** No component template references a Bootstrap class any
more — the only matches left are English words in comments and loop variables
named `row`. `styles.scss` already restates the parts of Bootstrap's reboot that
were load-bearing (`box-sizing`, heading/list margins, `img` display), so the
import and the `package.json` dependency can go. Do it behind a visual pass: the
reboot is exactly the kind of thing whose absence shows up as small layout
shifts rather than as a build error. Expect a large drop in `styles.css`, which
is currently 412 kB unminified, most of it Bootstrap.

**3. Add the CI spec-count guard's equivalent locally** if you run tests by hand
often — see the testing note in `console-ui.md`.

## Notes

Two prototype details were deliberately reinterpreted rather than dropped:

- **Dashboard composition.** The prototype shows a fixed layout; the app has
  user-reorderable widgets persisted per user, with tests covering it. The
  design's composition is the default order, and the reordering survives —
  "wide" widgets span the grid, the rest stack in the narrow column.
- **Document detail tab count.** The prototype has six tabs; the app has twelve
  areas of real functionality. All twelve ship, and the tab strip scrolls
  (`.dv-tabs--scroll`) rather than any feature being cut.

Three of the six conversion passes were interrupted by transient API errors
after finishing their edits but before reporting, so the Search, Sharing and
panels/public clusters may have gaps not yet listed here.

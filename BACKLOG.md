# Backlog

Consolidated open work for DocVault, grouped by priority.

**Sources merged into this file**
- `docs/design/console-ui-backlog.md` — design elements that need backend work
- `docs/design/console-ui.md` — "Migration status" section
- `REPO_REVIEW.md` — remaining items from the production-readiness review
- `dev/work/SPRINT-PLAN.md` — deferred/wontfix dispositions
- Findings from the Console redesign and Railway deployment pass (2026-07-31)

Items **verified as already done** are deliberately not repeated: drf-spectacular
schema warnings are at zero, `ruff` is in `requirements/dev.txt` and runs in CI,
and the `REPO_REVIEW.md` top-10 authorization/ingestion/share findings were
remediated in `2549c9e`. Re-check before assuming any regressed.

---

## P0 — Blocks real use of the deployment

### 1. Configure object storage on Railway
Uploads currently land on the web container's **ephemeral disk**, where the
Celery worker cannot see them and where they are lost on redeploy. Ingestion does
not work end to end in production until this is set.

Set on **all three** services (`web`, `worker`, `beat`), or configure in
**Admin → Storage**:

```
STORAGE_BACKEND=b2
S3_BUCKET_NAME=…    S3_ENDPOINT_URL=https://s3.<region>.backblazeb2.com
S3_REGION=…         S3_ACCESS_KEY=<keyID>    S3_SECRET_KEY=<applicationKey>
```

A Railway volume is not a substitute — volumes attach to a single service.
See `docs/storage-backends.md`.

---

## P1 — Correctness, delivery and cleanup

### 2. Confirm CI actually passes
The backend job had **never run green**: `python-magic-bin` has no Linux wheel so
the install step failed, and pytest lives in `requirements/test.txt`, which was
never installed. Both are fixed, but no successful run has been observed yet.
Watch the next push and confirm lint, migration check, deploy check and tests all
execute.

### 3. Add a smoke test that asserts styles actually apply
Production shipped with **no CSS at all** and every check still passed — the
stylesheet returned 200 and the HTML was correct. Only a computed-style check
caught it. Add a post-deploy smoke test asserting a known element's computed
style (e.g. `.dv-auth` resolves to `position: fixed`), so "asset loads" can never
again be mistaken for "asset applies".

### 4. Remove Bootstrap
No component template references Bootstrap classes any more, and `styles.scss`
already restates the load-bearing parts of its reset (`box-sizing`, heading and
list margins, `img` display). Removing the import and the dependency should cut a
large share of the 344 KB stylesheet.
Do it behind a visual pass: a missing reset shows up as subtle layout shift
rather than a build error.

### 5. Consolidate the duplicated `.dv-*` primitives
The redesign ran in parallel, so several components grew a local copy of a
pattern before it existed in `_console.scss`. The shared versions now exist;
collapse the duplicates onto them — mapping table in
`docs/design/console-ui-backlog.md` (banner, modal, row action, checkbox,
form row/grid, switch row, textarea/colour inputs, inline bulkbar).
This also clears the one remaining build warning:
`document-detail.component.scss` is 4.93 kB against a 4 kB per-component budget.
Hoist the duplicated rules rather than raising the budget.

### 6. Re-enable an HTTP health gate for `web`
`railway.json` applies repo-wide and `RAILWAY_CONFIG_PATH` does not override it,
so `/health/` had to come out of it — the Celery worker and beat serve no HTTP
and could never satisfy it. Set the healthcheck path on the **web service only**,
in the Railway dashboard.
Alternative: give worker/beat a small liveness endpoint and restore the
repo-wide config.

---

## P2 — Backend gaps blocking designed UI

About two dozen elements from the Console design could not be built because the
API does not expose the data. Each was **left out rather than filled with a
placeholder** — a fabricated accuracy figure or backup-code count reads as real
and is worse than an absent row.

Per-field detail: **`docs/design/console-ui-backlog.md`**. What needs API work:

| Area | Missing |
| --- | --- |
| Documents | version author/size, per-version download, notes count, AI page citations, an "unfiled" filter, saved-view document counts |
| Ingest | watch-folder path and last-polled (needs a wider list serializer), barcode PATCH endpoint, classifier accuracy/samples/algorithm, suggestions queue, scanner status/host, zone-OCR threshold and match count, AI endpoint/FAISS/feature flags, test-connection |
| Admin | per-user 2FA state and last-active, `is_superuser`, group member counts, role user-counts and descriptions, an object-level ACL endpoint for the permissions matrix, storage backends table, encryption metadata, integrity run timestamp |
| Workflows | step pipeline on the templates list, active-document count, trigger, escalation |
| Account | websocket-backed notification status, backup codes, active sessions, password age |
| Auth | no OIDC route exists, so the login "continue with SSO" affordance is omitted |

### 7. Object-storage migration tool
Switching backends does **not** move existing documents; anything written to the
previous backend stops resolving. The UI warns about this, but a management
command to copy objects between backends would make the switch safe.

---

## P3 — From the production-readiness review

Remaining items from `REPO_REVIEW.md` after its remediation pass:

- **Formal tenancy boundaries** — admin and tenant scopes are still broad.
- **Source credential storage** — integration credentials need proper secret handling.
- **Dependency locking** — no lockfile for Python; `requirements/*.txt` are ranges.
- **Observability** — beyond `/metrics/`: structured logs and error tracking (a
  `SENTRY_DSN` hook exists in `.env.example` but is unwired).
- **Ingestion durability** — the larger refactor: a durable ingestion record per
  source file (staged path, checksum, attempts, status, resulting document),
  shared by watch folders, S3, email, portal and scanner intake.
- **Container/Helm validation in CI** — the image is now known to build on
  Railway, but nothing validates the Helm chart or the image in CI.

---

## Deferred / wontfix

From `dev/work/SPRINT-PLAN.md`:

| Item | Decision | Rationale |
| --- | --- | --- |
| Mail OAuth refresh | Deferred | Needs registered OAuth app credentials |
| Visual workflow designer | Deferred | Large frontend effort, separate epic |
| User-facing docs tree | Deferred | Content work, not code |
| `@angular/localize` + locales | Deferred | i18n groundwork in `src/locale/README.md` |

### SMS verification delivery

Verification codes are provisioned and delivered out-of-band. Automatic SMS
delivery still needs a configured provider. SMS signers must complete code
verification before signing; email-link and no-additional-verification methods
retain their existing token-based behavior.

---

## Completed review fixes — 2026-10-24

Three review agents examined backend correctness, security, and frontend quality.
Confirmed findings were fixed with regression coverage:

- Webhooks now resolve and validate every destination address at connect time,
  connect to those exact addresses, and reject redirects and environment proxies.
- Confidential thumbnails use `private, no-store`, including conditional 304
  responses. Version activation and uploads enforce existing legal-hold checks.
- Signing checks persisted request/signer state, expiration, sequential order,
  and SMS verification. Stale views and expiration workers cannot overwrite
  terminal states; declining advances the next sequential invitation.
- Storage templates copy files before publishing the new filename and retain
  unique names. Overdue physical-record loans remain active and returnable.
- The SPA loads protected previews and downloads through authenticated HTTP
  requests and releases blob URLs. Iframe previews accept PDF content only.
  The frame CSP explicitly permits blob previews. Login accepts eight-character
  recovery codes.
- Search filter-builder rules reach the API, are validated against explicit
  fields/operators, and narrow the existing document permission scope.
- Removed unused stamp constants, misleading historical-version download links,
  obsolete migration/stub comments and repetitive comments in touched code.
  Replaced a certificate test that swallowed exceptions with an exact assertion.

Research references: [OWASP SSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html),
[OWASP transaction authorization](https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html),
[Django storage contracts](https://docs.djangoproject.com/en/5.2/ref/files/storage/),
and [Angular HTTP requests](https://angular.dev/guide/http/making-requests).

Existing deployment, tenancy, source-secret storage and dependency-locking work
above remains open. Automatic SMS delivery still needs provider configuration.

---

## Environment notes

Not backlog items, but each of these cost real time to rediscover.

- **Deploying from `/mnt/*` corrupts the upload.** `railway up` tars the working
  directory; from a Windows drive mount this injected NUL bytes into source
  files, surfacing only as `TS1127: Invalid character` in the remote Angular
  build while the local build was clean. `deploy/railway-deploy.sh` now stages
  `git archive HEAD` to the local filesystem first.
- **`VOLUME` is rejected by Railway** at Dockerfile validation — the build fails
  before any step runs and emits no build log.
- **Railway healthchecks send `Host: healthcheck.railway.app`** over plain HTTP
  on the internal network, so that host must be in `ALLOWED_HOSTS` and the health
  endpoints must be in `SECURE_REDIRECT_EXEMPT`.
- **`railway logs --build` defaults to the last *successful* deployment.** Pass
  the failed deployment's ID explicitly or you will read a stale, passing build.
- **The in-repo `.venv` is Windows-only.** A shared Linux venv lives at
  `~/.venvs/docvault`; put its `bin` on `PATH` rather than calling the
  interpreter by absolute path, since some tests shell out to `python`. See
  `dev/AGENTS.md`.
- **Vitest can exit 0 while skipping spec files** when a worker fails to start.
  CI now compares the reported file count against the files on disk.

# Feature verification and limitations

This records the 2026-10-25 acceptance campaign. Each README feature is mapped below to executed behavior or an explicit limit. A passing fixture proves that workflow under the stated configuration; it does not establish every permutation, provider, load level or AI answer as correct.

The application has substantial working functionality. This campaign also found broken backend wiring, authorization and persistence boundaries, and UI/API mismatches. The fixes and the tests belong together; the earlier feature list alone was insufficient evidence.

## Reproduce the local acceptance environment

Install Docker with Compose, Python 3.12+ and Node 22+, then run from the repository root:

```sh
cd src-ui
npm ci
npm run e2e:install
cd ..
python deploy/e2e.py --build --integrations
```

The isolated stack uses the production Docker build, PostgreSQL 16, Redis 7, separate Celery worker and Beat processes, Elasticsearch 8.19, Chromium, MinIO, GreenMail SMTP/IMAP, spaCy `en_core_web_sm`, Ollama `qwen2.5:1.5b` and `all-minilm` embeddings. AI calls have finite timeouts and bounded generation. The optional integration profile downloads model weights and builds MinIO from its pinned official source release.

Without `--integrations`, provider-dependent cases are skipped and the disabled-AI response is checked. That smaller run is not equivalent to the full acceptance run. `--keep --skip-tests` leaves the disposable environment available for debugging. The seed command refuses normal settings, even if the E2E flag is supplied. Test credentials are public fixtures confined to `docvault.settings.e2e`.

The main application publishes only `127.0.0.1:18086`. Infrastructure cases temporarily publish additional loopback ports and use disposable resources. Never point this suite at production: it intentionally exercises retention, quotas and other state-changing behavior. Production smoke tests use separate synthetic uploads.

CI builds the application and requires this integration profile. Failure screenshots, videos and Playwright traces are retained for seven days. Local reports are in `src-ui/playwright-report` and `src-ui/test-results`, ignored by Git.

## Execution evidence
[Strict GitHub CI for the initial accepted application commit](https://github.com/packetloss404/docvault/actions/runs/40223450800) passed **2,307 backend tests**, **653 Angular unit tests across 34 files**, and **all 73 acceptance checks** with no skips or retries. Ruff, migration consistency, production configuration checks, frontend build and Helm lint/render also passed.

The final local validation passed **2,328 backend tests**, **657 Angular tests across 35 files**, and all **73 acceptance checks in 10.0 minutes** from a fresh database and managed file store: **35 browser journeys**, **15 domain API cases**, **17 platform API cases** and **six infrastructure cases**. The combined acceptance run had no skips or retries. Development failures and traces were retained; targeted reruns were not substituted for this clean combined pass. See [main's CI history](https://github.com/packetloss404/docvault/actions/workflows/ci.yml?query=branch%3Amain) for subsequent release gates.

Deployment of [application commit 0b93425](https://github.com/packetloss404/docvault/commit/0b934251a1978f03ab707c9b059e81c30fec0fe2) was verified on 2026-10-25 after a private database backup and graceful worker shutdown. All six existing document downloads retained their checksums. New PDF/image uploads, OCR, private previews, original/archive downloads and anonymous-access rejection passed over HTTPS. Real Edge controls additionally verified login, upload, WebSocket status, dashboard refresh, two rendered pages, zoom, OCR text and checksum-correct downloads. The legacy backlog of 410 jobs drained to zero. Production uses local storage, PostgreSQL and Redis; optional AI, NER and Elasticsearch remain disabled there.

Evidence files:

- [Browser journeys](../src-ui/e2e/): the `browser-*.spec.ts` files operate real Chromium controls, rendered pages and downloads. Nineteen configuration-screen cases check actual API responses and rendering; they do not imply full CRUD coverage for every screen.
- [Domain API journeys](../src-ui/e2e/api-domain.spec.ts): collaboration, organization, workflows, legal holds, physical records, portals, notifications, retention and signing.
- [Platform API journeys](../src-ui/e2e/api-platform.spec.ts): OCR, versions, security, Elasticsearch, AI, classification, source ingestion, encryption and CAS.
- [Infrastructure journeys](../src-ui/e2e/api-infrastructure.spec.ts): metadata quotas, cross-process Redis caching, SMTP/IMAP, IP policy, GPG and a separate application using MinIO storage.

HTTP acceptance uses real application endpoints, persistent databases and independently running workers. A few infrastructure cases use guarded management code to provision keys, isolated files or storage fixtures; the user-facing flow still runs over HTTP. Unit tests separately cover negative paths and edge cases.

## Confirmed repairs

The failures extended into backend behavior. Jobs used a queue the worker did not consume; deployment found 410 stranded jobs, which drained after the routing correction and temporary legacy listener. Signing could review one version and certify another; requests now freeze and verify the same source/review bytes. Active-version downloads and viewer metadata, private storage-reference forgery, quota admission/persistence races, and concurrent FAISS/CAS publication received fixes and real regression checks.

Several apparent UI features also had incomplete wiring: security/admin endpoints and DTOs, portal form/review contracts, signature review pages, cabinet reorder, pinned saved views and WebSocket connection setup. Workflow field validation and scheduled triggers, legal-hold mutation guards, physical certificate PDFs and incoming-document linkage were repaired. These examples explain why a polished screen or an existing unit-test count alone was insufficient evidence.

A subsequent strict run caught the relationship graph collapsing connected nodes onto the canvas boundary; its successful retry correctly failed CI. Four deterministic regressions reproduce the original simulation instability. The repaired simulation passes all four, and the full Angular suite passes **657 tests across 35 files**. The browser case now checks node separation over 120 consecutive animation frames. Dependency resolution also now requests Celery's Redis extra: the previous image installed redis-py 8.1 outside Kombu 5.6.2's declared Redis compatibility range; the corrected resolver selects redis-py 6.4.

Further full-stack testing exposed two additional defects. Title generation inferred a president and a military purpose absent from the source; titles now select and validate a phrase from the actual document, excluding existing metadata from the prompt. A stack captured during a scheduler stall showed Beat blocked inside Redis Pub/Sub unsubscribe while finalizing unused periodic-job results. Periodic jobs now discard those results, following [Celery's guidance for unused results](https://docs.celeryq.dev/en/stable/userguide/tasks.html#ignore-results-you-don-t-want); ordinary document-ingestion result tracking remains enabled.

During the clean follow-up run, more than 3,000 periodic dispatches produced no Beat result subscriptions and no dispatch gap above two seconds. Watched/staged ingestion passed in 5.5 seconds. Five separate title probes, including an unrelated invoice, returned meaningful source phrases without retries. These are bounded regression checks rather than general latency or model-quality guarantees.

## Document management and organization

- **F01 — Upload and ingestion: locally verified, with provider limits.** Browser PDF upload and image drag-and-drop reach the worker, OCR, previews and checksum-correct downloads. Real SMTP delivery to GreenMail, IMAP attachment polling, watch/staging folders, MinIO source polling and contributor uploads are exercised. POP3 and mail OAuth token refresh are not implemented. External mailbox and cloud-provider configurations remain unverified. A previous CI watch-folder wait timed out; eight local repeats initially passed without retries. Retained logs and a later live stack capture located a scheduler stall in unused-result Pub/Sub cleanup. Periodic jobs now avoid those subscriptions, and the Redis client dependency respects Celery's compatibility bounds. E2E Beat DEBUG logs and full service logs are retained; CI rejects retry-only passes. This evidence does not establish a scheduling-latency guarantee.
- **F02 — OCR: locally verified.** An image-only invoice produces expected text, PDF/A metadata, page count, thumbnails and downloadable original/archive bytes through the real OCR pipeline. This is fixture validation, not an OCR accuracy benchmark or a comprehensive deskew/rotation quality assessment.
- **F03 — Zone OCR: locally verified.** A reference-image template extracts an invoice amount, supports correction/review and gives substantially lower confidence for a deliberately different layout.
- **F04 — Versions: locally verified with a reprocessing limit.** File upload, active-version selection, MIME/page/name/archive metadata, byte restoration, text diff and checkout are HTTP-verified. Browser checks cover activation, rendered pages and downloads; the text-comparison UI was not exercised. Replacement files do not automatically rerun OCR, classification or searchable-content/embedding generation. Older original-only documents remain readable and are registered lazily on their first version upload.
- **F05 — Barcodes: bounded live coverage.** A real QR separator produces two separately downloadable documents; ASN extraction and printable PNG labels are exercised. A focused unit integration test encodes/decodes CODE128. The live suite does not cover every supported 1D/2D symbology.
- **F06 — Tags: locally verified.** Hierarchy, colors, the five-level limit, matching/automation assignment and browser edits persist; a sixth level is rejected.
- **F07 — Cabinets: locally verified.** Hierarchy, API sibling moves and real browser sibling drag-and-drop persist in a fresh tree response; cycles are rejected. Hierarchy is changed through the parent control, not drag-to-nest.
- **F08 — Correspondents: locally verified.** Browser creation/assignment, matching rules and trained classification persist correspondent metadata.
- **F09 — Custom fields: locally verified.** All 12 field types round-trip through HTTP, including document-type assignments; workflow rules persist real values.
- **F10 — Document types and retention: locally verified with destructive-operation limits.** Types, field assignments and classifier output persist. A disposable policy executes through Beat/worker, removes eligible records and preserves held records. Permanent purge defaults to disabled and requires `RETENTION_HARD_DELETE_ENABLED=True`. Record purge is not secure erasure of storage copies, indexes or backups; month/year periods use 30/365-day approximations.
- **F11 — Storage paths: locally verified.** Jinja-based path selection affects actual stored/downloadable originals; autocomplete is exercised over HTTP.

## Search and AI

- **F12 — Full-text search: locally verified.** Real Elasticsearch hits, permission scoping, metadata/entity facets and index updates are checked; browser filters operate on an ingested document. Metadata visibility follows background indexing. The acceptance check waits for both the document and its updated tag facet within the existing timeout, since creation can become searchable before a later tag update.
- **F13 — Semantic search: locally verified.** Real embeddings are published by workers to FAISS and reloaded by web processes. Two concurrent ingests remain discoverable.
- **F14 — Hybrid search: bounded live coverage.** The configured local embedding/text path returns real results. Ranking quality across representative corpora has not been evaluated.
- **F15 — Global search: bounded browser coverage.** The command palette opens with Ctrl+K and navigates to the matching uploaded document. Not every entity category, platform shortcut or recent-query permutation is covered end to end.
- **F16 — Filter builder: locally verified.** Browser field/operator/value edits exclude and then include the expected document; permission-scoped query validation also has regression coverage.
- **F17 — Saved views: bounded browser coverage.** A saved title rule returns the uploaded document and both dashboard/sidebar pins navigate correctly. The full OR-group/filter combination space is not covered end to end.
- **F18 — Search analytics: locally verified.** Actual queries and clicks are recorded; analytics, synonym expansion and pinned curations are exercised against Elasticsearch.
- **F19 — LLM integration: local provider verified; external providers unverified.** Real Ollama chat returns the fixture's exact identifier and a source citation in the browser. Summary, title and structured entity endpoints retain expected source facts. Titles are extractive source phrases, bounded to 100 characters; inferred identities or purposes are rejected. OpenAI and Azure require live credentials and were not tested. Structured extraction now uses explicit instruction/document roles, a JSON schema and verbatim source checks; unsupported values cause an upstream-error response instead of successful fabricated entities. The smaller 0.5b model failed required recall and grounding checks; the acceptance profile uses the verified 1.5b model. This small known-fact check is not a general accuracy or hallucination evaluation. AI is optional and must be configured explicitly.
- **F20 — ML classification: locally verified.** Real labelled training, published model/hash reload and a fresh ingestion produce the exact expected type/correspondent and persisted suggestions with bounded probabilities. This is not a representative model-quality benchmark.
- **F21 — NER: locally verified.** Real spaCy extracts expected people/places; Elasticsearch entity facets and actual browser co-occurrence results are checked.
- **F22 — Vector embeddings: locally verified; clustering absent.** Index rebuild, independent process reload and concurrent publication are exercised. Document clustering is not implemented.
- **F23 — Redis stem cache: locally verified.** Two independent application processes write/read the same stem result through the configured Redis cache; this previously had no shared cache configuration.

## Collaboration and workflows

- **F24 — Comments: locally verified; flat only.** Browser and HTTP create/edit/delete work. Nested comment threads are not implemented.
- **F25 — Annotations: locally verified.** All eight visual tools persist against an actual rendered page; replies, deletion and JSON export are exercised. Export does not flatten annotations into the original PDF.
- **F26 — Shares: locally verified.** Wrong-password rejection, public browser access, checksum-correct download, download counter, revocation and clock expiry are checked.
- **F27 — Checkout: locally verified.** Checkout conflict/status/check-in work over HTTP and browser controls. Physical-record lending is a separate workflow below.
- **F28 — State machines: locally verified.** States, conditions, permitted transitions, lifecycle changes and persisted history are exercised.
- **F29 — Transition fields: locally verified.** Character/text, integer, boolean, date and select values are collected; required/invalid inputs fail and valid zero/false values survive. Browser controls and backend validation are covered.
- **F30 — Automation rules: locally verified.** Real consumption, creation, document update and scheduled triggers persist metadata/custom-field changes and launch a matching workflow through workers.
- **F31 — Escalations: locally verified.** A due escalation is executed by the independent Beat/worker processes and observed over HTTP.
- **F32 — State actions: partial live coverage.** Entry tagging and workflow effects are exercised. External email/webhook destinations have not been validated; their configuration and deliverability remain operator prerequisites.

## Signatures and security

- **F33 — Signature requests: locally verified.** Sequential/parallel ordering, actual page review, expiry, cancellation and certificate download are exercised. Requests freeze the selected version and title: switching the active document between signers cannot change reviewed bytes or the certificate's hash.
- **F34 — Public signing: locally verified.** Anonymous browser signing operates on actual review pages. Token access enforces expiry, cancellation, signer order and verification gates.
- **F35 — External signer verification: partial.** Protected review/completion is blocked before verification and invalid codes are rejected. Automatic SMS delivery and positive external delivery/provisioning were not validated; a trusted out-of-band code process is required.
- **F36 — Signature fields: locally verified with an output limit.** All five field types and page coordinates are stored and validated against the frozen artifact. The workflow creates an audit certificate; it does not flatten signature marks into a replacement original PDF or create a cryptographic GPG signature.
- **F37 — GPG: locally verified.** A real generated key signs stored PDF bytes, detached verification succeeds, a changed active version invalidates verification, and restoring the original makes verification succeed again. Production key provisioning/backup remains an operator responsibility.
- **F38 — Signing audit: locally verified.** Signed/completed events and actual certificate bytes are checked; source/review hashes identify the frozen artifact. Legacy active requests without snapshots fail closed with HTTP 409 and must be cancelled/reissued.
- **F39 — Authentication: password flow verified; generic OIDC unverified; LDAP/vendor social integration incomplete.** Browser login/error/logout/profile and HTTP authorization work. The generic django-allauth OpenID Connect provider and `/accounts/` routes are wired, but no live tenant was tested. LDAP is unavailable in the standard configuration: its setup helper is not invoked, its backend is unregistered and LDAP dependencies are undeclared. `LDAP_ENABLED=true` alone has no effect. Vendor-specific social providers require provider application/settings wiring; the social framework alone does not make them ready. A separate Mozilla OIDC wrapper is also unwired; use of its standalone flag/helpers is not validated.
- **F40 — Two-factor authentication: locally verified.** Browser QR enrollment, actual TOTP login, recovery and disable work; used recovery codes are rejected on reuse.
- **F41 — RBAC: locally verified.** Browser user/group/role creation persists assignments. HTTP group/role grants expose a document, view-only mutation is denied and revocation removes access. Ordinary users cannot load admin routes or APIs.
- **F42 — Object permissions: locally verified.** Cross-owner reads/mutations are denied unless granted. Ordinary metadata POST/PATCH cannot forge private original/archive/thumbnail storage references.
- **F43 — GPG: duplicate catalog entry.** Same evidence and limits as F37.
- **F44 — Encryption: storage integration verified.** Actual AES-GCM storage excludes plaintext, decrypts correctly and rejects tampering. Unit coverage includes configured version/snapshot storage compatibility. This does not claim every application workflow was rerun under every encryption/backend combination.
- **F45 — Audit logging: bounded live coverage.** Real login/actions appear in audit results and CSV export; the configuration screen renders. This is not proof of forensic completeness for every action or external tamper-proof retention.
- **F46 — Legal holds: locally verified.** Document capture blocks deletion and metadata/custom-field/bulk/workflow/supersession mutations; worker custodian notification, acknowledgment, export and release are exercised. Browser banners identify only held documents. Overrides require the explicit override permission.
- **F47 — CAS: storage integration verified.** Actual deduplication, corruption detection, bounded batched migration/readback/idempotence and four-process save/release reference counts pass on PostgreSQL. Migration operates existing `DocumentFile` rows and retains old physical copies; it is not an automatic original-only backfill or immediate disk reclamation. SQLite does not provide the same cross-process locking guarantee.
- **F48 — IP controls: bounded live coverage.** A separate web instance denies a disallowed client even with forged forwarding headers. Trusted-proxy parsing, allow/block lists and malformed addresses have unit coverage. Operators must configure `TRUSTED_PROXY_IPS`; arbitrary client headers are ignored.
- **F49 — Security headers: locally verified for delivered responses.** Actual denial responses include CSP/frame/content-type protections. HTTPS/HSTS is checked separately at the production proxy; local plain HTTP cannot prove TLS behavior.

## Physical records, portals and notifications

- **F50 — Locations: locally verified.** All five physical location levels persist through HTTP.
- **F51 — Charge-outs: locally verified.** Checkout, real scheduled overdue processing, return and recheckout are exercised.
- **F52 — Barcode checkout: locally verified.** Scan-code checkout/return works and duplicate active checkout is rejected.
- **F53 — Destruction certificates: locally verified as attestations.** A witnessed record produces an authenticated downloadable PDF. Software cannot establish that physical destruction occurred.
- **F54 — Public portals: locally verified.** A branded portal created in the browser accepts required contributor inputs and a real anonymous document upload.
- **F55 — Document requests: locally verified with delivery limits.** Token request/send/remind, partial fulfillment and deadline rejection run against the local mail backend. External delivery remains unverified.
- **F56 — Submission review: locally verified.** Browser approval and independent ingestion link the managed document; its original downloads with the expected checksum.
- **F57 — Real-time notifications: bounded browser coverage.** An actual task-status WebSocket frame triggers an ingestion/dashboard update. This does not establish a separately asserted notification-channel frame. Reconnect logic has unit coverage; prolonged network-loss behavior and multi-node failover were not exercised.
- **F58 — Preferences: locally verified for persistence/in-app behavior.** Event preferences and read/read-all counts persist with owner scoping. Local mail-backend messages prove configured delivery, not external SMTP or arbitrary webhook delivery.
- **F59 — Quotas: locally verified with an accounting limit.** Metadata creation, incoming bytes, version bytes and two concurrent uploads enforce owner limits; only one competing document persists. Older original-only records enter byte accounting when registered as managed files. Logical storage accounting covers managed original/version bytes, not previews, archives, staging, signing snapshots or total host disk usage. Group/user configurations have unit coverage; not every overlapping group policy was exercised live.
- **F60 — Relationship types: locally verified.** Configurable links produce real graph nodes/edges over HTTP and in the browser.
- **F61 — Supersession: locally verified.** Creating/removing a superseding link sets/clears obsolete state.
- **F62 — Relationship graph: locally verified.** Actual browser SVG nodes and their connecting edge render from persisted relationships. Multi-frame checks reject the previously observed collapse of connected nodes onto the same canvas boundary; deterministic tests also cover drag/release and recovery from collapsed positions.

## Deployment scope and remaining prerequisites

Local MinIO validates the S3-compatible path; AWS, B2, R2 and other provider-specific behavior still require their own credentials and live checks. OpenAI/Azure, external generic OIDC, external SMTP and SMS remain live-unverified by explicit agreement. LDAP and vendor-specific social providers additionally require integration work before use. Those claims must not be inferred from a green local CI run.

The Helm chart is linted/rendered in CI; no Kubernetes cluster deployment is claimed. The production Compose deployment enables only its configured services. Passing optional local AI/search/storage tests does not enable those services in production automatically.

This campaign is functional and regression validation, not a penetration test, load test, disaster-recovery exercise or compliance certification. Known limits above remain visible instead of being represented as completed features.

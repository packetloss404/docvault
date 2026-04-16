# Instructions for coding agents (DocVault)

Use this file as the **onboarding brief** before changing the repo.

## 1. Where work is defined

| Read first | Purpose |
|------------|---------|
| **[`work/CHECKLIST.md`](work/CHECKLIST.md)** | Ordered open tasks (checkboxes). Pick a section or a single item. |
| **[`work/features/FEAT-NG-*.md`](work/features/)** | Acceptance criteria for **§ A** (NextGen UI items). Open the FEAT that matches your task. |

## 2. Repository map (where to implement)

| Area | Path |
|------|------|
| Angular SPA | `src-ui/src/app/` — components, `services/`, `app.routes.ts`, `environments/environment.ts` (`apiUrl` → `http://…/api/v1`) |
| Django apps | Repo root: `documents/`, `security/`, `search/`, `organization/`, `processing/`, `collaboration/`, … |
| Django project | `docvault/` — `settings/`, `urls.py` |
| API contract | `GET /api/schema/` (OpenAPI) when unsure of paths or bodies |

## 3. Workflow

1. Choose a **checkbox** in [`work/CHECKLIST.md`](work/CHECKLIST.md) (or a whole subsection if doing a batch).
2. If it maps to **§ A**, read the matching [`work/features/FEAT-NG-…`](work/features/) file for acceptance criteria and file pointers.
3. Implement in **small, focused PRs**—match existing patterns in neighboring files.
4. When an item is **done**:
   - Change `- [ ]` → `- [x]` in `work/CHECKLIST.md` for that line (and any duplicate theme line if applicable).
   - In `work/features/FEAT-NG-*.md`, set **`Status:`** to `done` and add a one-line **Shipped:** note with PR or date if helpful.
5. If you **defer** or **wontfix** an item, note it in the FEAT file (`Status: wontfix`) with a short rationale—do not leave silent gaps.

## 4. Rules of thumb

- Prefer **existing** services and components; extend rather than re-scaffold.
- Verify HTTP paths against **`docvault/urls.py`** and the app’s `urls.py`—no guessed `/security/` prefixes.
- After UI work, **smoke-test** the happy path (login → feature) if you can run the stack.
## 5. Quick links

- [`README.md`](README.md) — index of `dev/`
- [`work/README.md`](work/README.md) — `work/` folder index

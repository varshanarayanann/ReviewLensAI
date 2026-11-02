# ReviewLens AI — Engineering Coding Standards

**Story:** S1-001 — Create Engineering Coding Standards Context Document

**Rule references:** S1-BR-004, S1-BR-007, S1-BR-011

**Audience:** Team developers, reviewers, and AI coding tools modifying this repository.

**Baseline reviewed:** 2026-11-02, `main` at `624bbf1`.

## 1. Using this context

Read the active story, this document, and the relevant source before editing code.
For screen changes, also read [UI/UX standards](ui-ux-standards.md). Use the
[README](../../README.md) for setup and [AGENTS.md](../../AGENTS.md) for project
context. Supply these files and the active acceptance criteria to AI coding tools;
review and test generated changes using the same standards as other team code.

This document records the repository's chosen approach. Tool configuration and
committed manifests establish what is mechanically enforced; additional conventions
below are review expectations. If a story changes a convention, update the relevant
documentation, configuration, and tests in the same PR. Resolve conflicts explicitly
rather than silently replacing an existing contract.

The rule IDs above come from the story. Their full definitions are not included in
the local requirements, so this document does not invent definitions for them.

## 2. Repository organization and boundaries

ReviewLens is a monorepo with independently installed and checked applications:
React/TypeScript/Vite in `frontend/`, and Python/FastAPI/SQLAlchemy in `backend/`.
Supabase provides Auth and PostgreSQL. There is no root npm workspace or root test
command. Run commands from the application directory, especially backend commands
because settings load `.env` relative to the working directory.

| Location | Put changes here |
| --- | --- |
| `frontend/src/main.tsx`, `App.tsx` | Startup configuration, dependency injection, providers, and route declarations |
| `frontend/src/pages/` | Route-level components and page behavior |
| `frontend/src/components/ui/` | Reusable controls such as `TextField`, `Alert`, and `Skeleton` |
| `frontend/src/components/layout/` | App shell, auth layout, account menu, and route guards |
| `frontend/src/lib/api/` | Typed HTTP calls and `ApiError`; keep fetch logic out of pages |
| `frontend/src/lib/auth/` | Auth state, session lifecycle, auth error mapping, and credential validation |
| `frontend/src/lib/messages.ts` | Shared user-facing messages; reuse these instead of duplicating error copy |
| `frontend/src/styles/tokens.css`, `index.css` | Design variables and shared styling; follow the UI standards |
| `frontend/src/**/*.test.ts(x)`, `src/test/` | Colocated frontend tests and shared test helpers |
| `backend/app/main.py` | `create_app` factory, middleware, and router registration |
| `backend/app/api/` | HTTP endpoints and orchestration; register new routers in `create_app` |
| `backend/app/auth/` | Verified identity, JWT/session verification, and protected-route dependencies |
| `backend/app/schemas/` | Pydantic request/response contracts and boundary validation |
| `backend/app/models/` | SQLAlchemy persistence models and shared declarative base |
| `backend/app/config.py`, `db.py` | Settings, engine configuration, and request-scoped database sessions |
| `backend/tests/` | pytest tests and fixtures |
| `backend/migrations/` | Ordered SQL migrations; follow the [migration policy](../../backend/migrations/README.md) |
| `docs/context/`, `.github/workflows/` | Team conventions and automated delivery checks |

The browser may use the Supabase Auth SDK for accounts and sessions. Application
data goes through FastAPI; do not access application tables or review providers
directly from the browser. Keep source-specific parsing separate from UI code.
Extend the existing layers and shared components before introducing abstractions
or a new service/repository framework.

Current domain code supports target creation/read and synchronous CSV ingestion.
Google Maps is the fixed platform. Automatic URL collection, target listing,
summaries, and AI Q&A must not be presented as implemented capabilities.

## 3. Naming conventions

| Area | Convention and existing example |
| --- | --- |
| Python modules, functions, variables | `snake_case`: `analysis_target.py`, `get_current_user`, `target_id` |
| Python classes and Pydantic models | `PascalCase`: `AnalysisTarget`, `AnalysisTargetCreate`, `IngestionResult` |
| React component files and components | `PascalCase`: `DashboardPage.tsx`, `AppShell` |
| TypeScript utilities and ordinary values | `camelCase`: `getCurrentUser`, `accessToken`; retain existing module names such as `authErrors.ts` |
| TypeScript types/interfaces | `PascalCase`: `AppConfig`, `CurrentUserResponse` |
| Constants | Follow existing uppercase shared constants such as `MESSAGES` |
| Database and JSON fields | `snake_case`: `owner_id`, `source_url`, `persisted_count`; frontend wire types retain these field names |
| Database tables | Plural `snake_case`: `analysis_targets`, `ingestion_runs`, `reviews` |
| Tests | Python `test_*.py` / `test_*`; frontend `*.test.ts` or `*.test.tsx` |
| CSS | Reuse tokens and existing class patterns, for example `button--primary`; do not introduce another naming system |
| SQL migrations | Ordered numeric prefix and descriptive name, for example `0002_create_ingestion_runs_and_reviews.sql` |

Use the product terms Analysis target, Dashboard, Analysis workspace, Google Maps,
and Ingest reviews in user-facing copy. Keep names aligned across schema, API, and
UI instead of introducing synonyms for the same entity.

## 4. Formatting, types, and linting

Python uses four-space indentation, type annotations for interfaces, and Ruff's
formatter with Python 3.12 as its target and an 88-character line length.
`backend/pyproject.toml` enables Ruff `E`, `F`, and `I` checks, including import
ordering. Use `python -m ruff format .` to format changed Python code; review the
diff to avoid unrelated formatting changes.

Frontend code uses typed function components, two-space indentation, single-quoted
TypeScript strings, no semicolons, and type-only imports where appropriate. Follow
surrounding JSX style. `frontend/.oxlintrc.json` enables React, TypeScript, and Oxc
plugins; hooks violations are errors and component-export checks are warnings.
`npm run build` runs `tsc -b` before Vite, so type errors are build failures.
There is no committed Prettier command or separate `typecheck` script.

Do not suppress lint/type errors or weaken configuration to make a change pass.
Any necessary exception must be narrow and explained in the PR. Use shared CSS
tokens, semantic controls, accessible labels, and the UI document's responsive
checks for screen changes.

## 5. Authentication, validation, and error handling

- Protect backend operations with `Depends(get_current_user)`. Frontend route
  guards improve navigation but do not authorize API calls.
- Derive ownership from verified `CurrentUser.id`, never a client-supplied owner.
  Query targets by both ID and owner. Authorize the parent before review access,
  ingestion, or any other child operation. Missing and inaccessible targets both
  return 404; denial must not create an ingestion run or mutate stored records.
- Validate authoritative inputs with Pydantic schemas, mirroring useful checks in
  the UI. For example, `AnalysisTargetCreate` trims names, requires 1–120 characters,
  rejects extra fields, and parses allowed HTTPS Google Maps URLs. Do not replace
  parsed host/path checks with substring matching.
- Handle expected failures at the boundary that can recover or translate them.
  Use `HTTPException` for controlled HTTP errors and safe, actionable UI copy.
  Never render raw Supabase errors, FastAPI validation dumps, SQL errors, or
  arbitrary exception messages in the UI. Use the shared auth/message mapping.
- Frontend HTTP helpers throw status-bearing `ApiError` on non-success responses.
  On protected-request 401, use the auth provider's session-expiry flow. Distinguish
  network failure from a server response; preserve non-password form input on failure.
- `get_db` closes sessions but does not commit automatically. Writes need explicit
  commit/rollback handling. Do not report successful persistence before commit.
- CSV ingestion records an attempt separately, then commits reviews and the success
  outcome together. A rejected import or persistence failure rolls back that batch,
  records failure, and preserves earlier reviews. The route's broad exception catch
  supports that recovery boundary; it is not a pattern for silently swallowing
  exceptions elsewhere. Never substitute sample reviews after a failed import.

Do not assume Supabase RLS protects SQLAlchemy queries. Preserve backend ownership
checks independently of any database policy. Keep credentials in ignored `.env`
files, update `.env.example` when configuration changes, and treat every `VITE_*`
value as browser-visible. Database credentials and secret/service-role keys belong
only on the server.

## 6. API and response conventions

Routes live under `/api`; use the existing JSON field names and HTTP semantics.
The API currently returns resource objects directly, without a universal
`{ data, error }` envelope. Do not introduce an envelope on individual endpoints.
Use Pydantic models for new or changed structured contracts, and update frontend
wire types and behavior tests together. Existing target responses are explicit
dictionaries; ingestion already uses `response_model=IngestionResult`.

| Situation | Existing contract to preserve |
| --- | --- |
| Successful read | 200 with JSON; latest ingestion returns JSON `null` when no run exists |
| Target creation | 201 with `id`, `name`, and `source_url` |
| Invalid request | FastAPI/Pydantic 422; the UI maps it to safe validation copy |
| Missing/invalid authentication | 401 and `WWW-Authenticate: Bearer` |
| Auth infrastructure unavailable | 503, distinct from invalid credentials |
| Missing or another user's target | 404 with the same safe detail |
| Handled ingestion outcome | 200 with `run_id`, `target_id`, `state`, `persisted_count`, and `message`; inspect `state` to determine success |

FastAPI `HTTPException` errors use `detail`; request validation uses FastAPI's
standard validation structure. The database health endpoint has its own documented
503 body, `{"database":"unavailable"}`. Do not assume all errors share a custom
schema or that HTTP 200 means an ingestion succeeded.

Ingestion states are `processing`, `succeeded`, and `failed`. Counts come from
persisted outcomes: success requires a positive count, while processing/failed
results report zero. Current CSV input is JSON containing `csv_text`, not a
multipart upload. It requires `rating` and `review_text` columns, integer ratings
1–5, nonblank trimmed text, at most 1,000 reviews, and at most 1,000,000 characters
in the API field. The UI also limits the selected file to 1,000,000 bytes. Invalid
rows reject the entire batch; no partial-success contract is implemented.

## 7. Logging expectations

Use Python's standard `logging` module and a module logger,
`logger = logging.getLogger(__name__)`. The app configures logging at INFO in
`create_app`; do not add per-module global configuration or diagnostic `print`s.

Log enough to diagnose the operation safely. Existing auth code logs rejected
tokens at INFO using controlled verifier reasons. Ingestion logs a warning with
the run ID and exception class, using parameterized formatting:

```python
logger.warning("Ingestion %s failed (%s)", run_id, type(exc).__name__)
```

Never log bearer tokens, passwords, keys, connection strings, CSV/review contents,
or SQL driver parameters. Existing auth infrastructure handling uses
`logger.exception`; do not copy traceback logging into paths whose exception text
could contain sensitive payloads or credentials. Use sanitized reasons and IDs
instead. Add log-redaction assertions when changing failure paths involving
sensitive data. Do not send secrets or review payloads to browser console logs.
No external logging platform or JSON log schema is currently configured.

## 8. Dependencies and configuration changes

- Use the committed manifests as the authority: `frontend/package.json` and
  `package-lock.json`, plus backend `requirements.txt` and `requirements-dev.txt`.
  Node 22 and Python 3.12 are the CI baselines; backend supports Python 3.12+.
- Reuse installed libraries and standard-library features first. Explain a new
  dependency's purpose, maintenance/security implications, compatibility, and
  runtime versus development placement in the PR. Verify the package identity and
  API against authoritative documentation; AI-generated package names are not evidence.
- Use `npm ci` for an unchanged checkout. When intentionally adding/changing an npm
  dependency, use `npm install` and commit both manifest and lockfile changes.
  Keep backend runtime requirements separate from dev-only tooling; the backend
  currently uses bounded ranges rather than a committed lockfile.
- Retain declared dependencies unless the task calls for changing them. In
  particular, the dev manifest actually declares `httpx2`; do not silently rename
  it based on familiarity with another package.
- Do not introduce a CSS framework, alternate auth stack, or provider/LLM SDK as an
  incidental change. Keep provider credentials server-side. Update setup docs,
  configuration validation, `.env.example`, tests, and CI when a dependency changes
  how the project is installed or run.

## 9. Testing and delivery expectations

Add or update behavioral tests for changed application behavior, including success,
validation failure, and recovery paths relevant to the story. Bug fixes should
include a regression test. Documentation-only changes need link/content review,
not new application tests. Keep tests deterministic using injected dependencies,
fake auth clients, mock transports, and controlled fixtures.

Frontend uses Vitest, jsdom, and Testing Library, with shared cleanup and fake auth
in `src/test/`. Test user-visible behavior, routing, submission states, safe error
copy, and session changes. Backend uses pytest and FastAPI test clients; reuse
fixtures for signed JWTs and fake session checks rather than disabling auth.

For owned resources, test two users, permitted access, denied reads/mutations,
correct target association, and unchanged records after denial. In ingestion work,
test malformed records, persistence failures, persisted counts/states, and retention
of previous reviews. Tests must verify outcomes, not only status codes.

`test_target_workflow.py` runs against SQLite and PostgreSQL. CI provisions
PostgreSQL 18 and sets `TEST_POSTGRES_URL`; the PostgreSQL fixture applies the actual
SQL migrations in a temporary database with a minimal `auth.users` table. Locally,
that variant skips without the variable. Use only a disposable PostgreSQL server
with database creation/drop permissions for it. SQLite does not establish
PostgreSQL migration equivalence, and these tests do not prove live Supabase Auth
logout/revocation behavior. Report skipped integrations explicitly.

Run the relevant checks before submitting a PR. For changes affecting both apps,
run both sets. Commands match the current CI workflow:

```powershell
# From frontend/
npm run lint
npm run build
npm test
```

```powershell
# From backend/, with the virtual environment active
python -m ruff check .
python -m ruff format --check .
python -m compileall -q app tests
python -c "from app.main import create_app"
python -m pytest -ra
```

Use a PR for delivery. State the problem, changed behavior, story reference, tests
run, and any skipped checks or integration limits. Review the full diff, including
AI-generated code, dependency changes, migrations, and secrets. Never edit a
migration already applied to a shared database; add the next ordered file.

The expected checks are **Frontend**, **Backend**, and **Secrets**. Secrets checks
reject committed `.env` files except `.env.example` and scan full Git history with
gitleaks. If a secret is exposed, rotate it; deleting the current file is insufficient.
Follow the README's PR, passing-check, up-to-date-branch, and no-bypass policy;
workflow success alone does not prove GitHub branch protection is configured.

## 10. Review checklist

- [ ] The change satisfies the active story and uses the existing folder boundaries.
- [ ] Names, formatting, types, and UI conventions match this context and tool config.
- [ ] Auth, ownership, validation, and transaction behavior remain correct.
- [ ] Responses and logs expose safe information and reflect actual outcomes.
- [ ] Dependencies and configuration changes are justified and documented.
- [ ] Behavioral tests cover the change and relevant failures/isolation boundaries.
- [ ] Relevant checks passed; skipped checks and external verification limits are stated.
- [ ] Contracts, setup instructions, and context documents are updated where needed.

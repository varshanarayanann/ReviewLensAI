# ReviewLens AI — Project Context and Agent Guide

## 1. Scope, evidence, and how to use this file

This guide applies to the entire ReviewLens AI repository. Read it before changing code, then read the active story and relevant source files. Keep it current when architecture, commands, contracts, or scope change.

Research snapshot: **2026-11-01**, default branch `main`, commit **`aeb68cc7c6bdaf1812ffc6ef996a440b3b6e39e1`**. Board statuses, branches, and PRs below are dated observations, not permanent facts. Recheck them before starting overlapping work.

- Repository: <https://github.com/varshanarayanann/ReviewLensAI>
- Project: [CS 490 JAVBN Kanban Board](https://github.com/users/varshanarayanann/projects/2).
- Repository description calls the team **JAVNB**; the board uses **JAVBN**. Preserve existing names rather than assuming one spelling is authoritative.
- Requirements available locally: [Sprint1Issues.csv](Sprint1Issues.csv), containing all 23 Sprint 1 stories and their business-rule references.
- Setup and delivery baseline: [README.md](README.md).
- Detailed UI specification: [docs/context/ui-ux-standards.md](docs/context/ui-ux-standards.md).
- Database change policy: [backend/migrations/README.md](backend/migrations/README.md).

**Evidence labels in this guide:** implemented means present in the inspected `main`; planned means required by stories or team documentation; branch-only means inspected but unmerged. A closed issue or a Done board card does not prove its files exist on `main`.

The UI document gives this requirement precedence: active sprint story → instructor UX reference → team architecture baseline → UI standards → developer preference. The instructor UX reference/image, standalone architecture baseline, full PRD, technical specification, and full business-rule catalog were not present in the inspected repository. Do not invent their contents or treat references to them as verified evidence. Use source code to establish current behavior, and requirements to establish intended behavior; document discrepancies.

## 2. Product and sprint boundaries

ReviewLens AI is a multi-user **Review Intelligence Portal**, built as a CS 490 capstone. A user authenticates, creates analysis targets for Google Maps businesses, collects and persists their reviews, and eventually asks questions grounded only in the authorized reviews.

The intended user journey is:

1. Register/log in through Supabase Auth.
2. Open the dashboard containing only the current user's targets.
3. Create a target with a name, fixed Google Maps platform, and source URL.
4. Open that target's analysis workspace.
5. Ingest reviews from its saved URL; use CSV import as the documented fallback.
6. See an explicit ingestion result and persisted reviews.
7. In Sprint 2, inspect review summaries and ask review-grounded questions.

| Phase | Intended scope | Verified delivery state |
| --- | --- | --- |
| Sprint 1 | Context documents, tooling/CI, managed auth, ownership isolation, targets, review ingestion and persistence, basic ingestion states | Foundation and auth are on main; much of the domain workflow remains unimplemented |
| Sprint 2 | Review summary/statistics, charts, review-grounded Q&A | Future scope; no implementation on main |
| Sprint 3 | Netlify frontend and Render backend deployment | README deployment plan; no deployment configuration or verified live deployment found |

Google Maps is the selected platform. Do not add a multi-platform selector. The UI baseline chooses URL ingestion as primary and CSV as recovery; generic story #19 permits either URL or practical import, so preserve the team's more specific baseline unless the active requirements change. No concrete review-data provider is selected in the inspected implementation. An outside suggestion on issue #20 is not a team decision.

Do not add Summary/Ask tabs, AI chat, rating charts, or “coming soon” placeholders to Sprint 1 work unless explicitly required by the active task. There is no LLM SDK, model selection, vector database, embedding pipeline, or implemented Q&A API on main.

## 3. Current implementation and repository map

The repository is a frontend/backend monorepo with independent dependency and test commands. There is no root npm workspace, Docker setup, application task runner, or automated migration runner on main.

| Path | Role and current contents |
| --- | --- |
| `frontend/package.json`, `package-lock.json` | npm scripts, dependency declarations, reproducible frontend resolution |
| `frontend/src/main.tsx` | Loads config, creates Supabase client, mounts StrictMode/BrowserRouter/App; displays a safe configuration error on invalid config |
| `frontend/src/App.tsx` | Injected config/auth client, AuthProvider, route declarations |
| `frontend/src/lib/config.ts` | Required public environment configuration and Supabase secret-key detection |
| `frontend/src/lib/supabase.ts` | Supabase client with session persistence, automatic refresh, URL session detection |
| `frontend/src/lib/auth/` | Auth context/provider, auth error mapping, email/password validation |
| `frontend/src/lib/api/client.ts` | Typed health/current-user fetch functions and status-bearing `ApiError` |
| `frontend/src/lib/messages.ts` | Shared user-facing auth/error messages |
| `frontend/src/components/layout/` | AppShell, AuthLayout, AccountMenu, route guards and shell skeleton |
| `frontend/src/components/ui/` | Currently only Alert, Skeleton, TextField |
| `frontend/src/pages/` | LoginPage, RegisterPage, DashboardPage, NotFoundPage |
| `frontend/src/styles/tokens.css`, `index.css` | Design variables and existing layouts/component styling |
| `frontend/src/App.test.tsx`, `src/lib/config.test.ts`, `src/test/` | UI/config tests, fake auth client, test cleanup |
| `backend/app/main.py` | FastAPI factory; config/verifier injection, CORS, router registration |
| `backend/app/config.py` | Pydantic Settings, sanitized config errors, cached default settings |
| `backend/app/db.py` | Cached SQLAlchemy engine, psycopg URL conversion, request-scoped sessions |
| `backend/app/auth/tokens.py` | CurrentUser, JWT verification, signing-key and session-check interfaces |
| `backend/app/auth/dependencies.py` | HTTP Bearer dependency and safe 401/503 responses |
| `backend/app/api/health.py`, `me.py` | The three implemented API operations |
| `backend/tests/` | Configuration, JWT/authentication, session-check transport, health and CORS tests |
| `backend/migrations/` | Migration policy README only on main; no SQL migrations yet |
| `docs/context/` | UI/UX standards only on main |
| `.github/workflows/ci.yml` | Frontend, Backend, Secrets checks |
| `.github/workflows/import-sprint-issues.yml` | Manually triggered CSV-to-GitHub issue importer, currently embedded Python |
| `Sprint1Issues.csv` | Issue-import seed and Sprint 1 requirements, not a review-data fixture |

### Stack

Use the committed manifests and lockfile as the version authority. At this snapshot:

- Node.js **22+**; CI uses Node 22.
- React `^19.3.1`, React DOM `^19.3.1`, React Router `^7.18.5`, Supabase JS `^2.118.0`.
- TypeScript `~7.0.2`, Vite `^8.3.5`, Vitest `^5.0.5`, jsdom `^29.1.1`, oxlint `^1.89.0`, Testing Library.
- Python **3.12+**; CI uses Python 3.12.
- FastAPI `>=0.115,<1`, Uvicorn `>=0.32,<1`, pydantic-settings `>=2.6,<3`, SQLAlchemy `>=2.0,<3`, psycopg binary `>=3.2,<4`, PyJWT crypto `>=2.10,<3`.
- Backend dev tools: pytest `>=8.3,<9`, Ruff `>=0.11,<1`, and **`httpx2>=2.16,<3` as actually declared**. Do not silently replace this dependency based on an assumed package name.
- PostgreSQL hosted by Supabase; managed authentication through Supabase Auth.
- Plain CSS and shared tokens. No Tailwind or UI component framework is installed. `lucide-react` is mandated by UI standards for icons but is not yet in package.json.

## 4. Runtime architecture and authentication

```text
Browser / React SPA
  ├── Supabase JS → Supabase Auth (registration, login, sessions, logout)
  └── typed API client → FastAPI /api/*
                           ├── JWT verification → Supabase public JWKS
                           ├── session check → Supabase Auth /auth/v1/user
                           └── SQLAlchemy + psycopg → Supabase PostgreSQL

Planned: authorized target → ingestion adapter → normalization → Review persistence
                                                     └──────→ IngestionRun result
```

The browser may call Supabase **Auth** through its SDK. Application data operations go through FastAPI; do not directly query review storage or call a review provider/AI service from the frontend.

### Frontend session flow

- `main.tsx` creates the configured client and injects `supabase.auth` into `App` for testability.
- `AuthProvider` restores `getSession()` and subscribes to `onAuthStateChange`; states are `loading`, `authenticated`, and `unauthenticated`.
- Protected pages display a shell skeleton during restoration. Logged-out navigation saves the pathname/query in router state and redirects to `/login`.
- Login uses `signInWithPassword`. Registration uses `signUp` with a `/login` email redirect, and distinguishes immediate sign-in, confirmation-required, and an existing-account response.
- Registration validates email, a minimum eight-character password, and matching confirmation. Password policy must also agree with Supabase settings.
- Return paths must start with `/` and must not start with `//`; keep this guard against external redirects.
- The dashboard calls `/api/me` using the access token. A 401 expires the local session and displays the shared session-ended message; other API failures are mapped to safe UI messages.
- `signOut()` clears local session state in `finally`; AuthProvider also handles auth changes from elsewhere. Clearing local state alone does not prove remote revocation succeeded.

### Backend trust boundary

- Use `Depends(get_current_user)` for every protected operation. `CurrentUser.id` comes from verified JWT `sub`; email is optional.
- Tokens require `exp`, `sub`, `aud`, and `iss`. Audience must be `authenticated`, issuer must match the configured project `/auth/v1`, and algorithms are limited to **ES256/RS256**. HS256 is rejected.
- JWKS lives at `<SUPABASE_URL>/auth/v1/.well-known/jwks.json`. `PyJWKClient` caches signing keys and uses a five-second timeout.
- After signature/claims verification, `SupabaseSessionChecker` calls `/auth/v1/user` with the bearer token and public API key. Remote 401/403 becomes an invalid token; transport errors/other HTTP failures become authentication unavailability.
- Invalid/missing authentication returns 401 with `WWW-Authenticate: Bearer`. Authentication infrastructure failure returns 503 rather than treating the user as authorized.
- Tests simulate revoked tokens and remote responses. They do **not** prove that the live Supabase project rejects every copied token immediately after logout. Verify this integration behavior against a real test project before asserting that guarantee; README/PR #26 describes the intended behavior.
- CORS is configured explicitly, but it is not an authorization mechanism.

### Database behavior

`get_engine()` converts `postgres://` and `postgresql://` to `postgresql+psycopg://`, enables `pool_pre_ping`, and sets a five-second connection timeout. `get_db()` yields a session and closes it; it does **not** automatically commit. Future writes need explicit transaction handling.

`create_app(settings=...)` injects settings for app/auth configuration, but the database engine still reads cached global `get_settings()`. Tests of database behavior should override `get_db` or isolate caches/configuration explicitly; injected app settings alone do not reconfigure the database.

## 5. Actual routes and API contracts

### Frontend routes on main

| Route | Behavior |
| --- | --- |
| `/` | Auth-dependent redirect to dashboard or login |
| `/login`, `/register` | Public-only auth pages; authenticated visitors redirect |
| `/dashboard` | Protected shell and backend-verified identity; target list is still placeholder copy |
| `*` | Public Not Found page |

**Specified but not implemented:** `/forgot-password`, `/reset-password`, `/targets/new`, `/targets/:targetId`. The desired authenticated shell includes a sidebar, breadcrumbs, and active-target context; main currently has a header and content area only.

### API operations on main

| Method/path | Auth | Response |
| --- | --- | --- |
| `GET /api/health` | Public | 200 `{"status":"ok"}`; does not test database health |
| `GET /api/health/db` | Public | Runs `SELECT 1`; 200 `{"database":"ok"}` or handled SQLAlchemy failure → 503 `{"database":"unavailable"}` |
| `GET /api/me` | Bearer token | 200 `{"id":"<verified subject>","email":"<email or null>"}`; invalid/missing token → 401; auth infrastructure failure → 503 |

FastAPI's `/docs` is enabled outside production; ReDoc is disabled. Setting `ENVIRONMENT=production` disables `/docs`, but the code does not disable the default OpenAPI JSON route.

The UI standards reference `/api/targets`, `/api/targets/{id}/ingestions`, deletion, and later `/api/targets/{id}/ask`. These are **proposed contracts**, not available endpoints. No implemented review listing, ingestion, or target CRUD API exists on the inspected main branch.

## 6. Domain model, ownership, and ingestion requirements

### Required domain relationships

```text
Verified Supabase user
  └── owns AnalysisTarget (many)
        ├── contains Review (many)
        └── records IngestionRun (many)
```

This is the intended relationship model, not a complete implemented schema.

| Entity | Required semantics | Implementation status |
| --- | --- | --- |
| User identity | Stable verified Supabase subject; no application password storage | CurrentUser value object exists; no separate application User table on main |
| AnalysisTarget | Unique ID, owner, name, supported platform, source reference, creation timestamp | PR #27 proposes model and migration; absent from main |
| Review | Review text and rating; linked to intended target; preserve source metadata when available | Not implemented |
| IngestionRun | Separate attempt record/context, target association, success/failure and processing if asynchronous; optional partial success | Not implemented |

PR #27 specifically proposes `analysis_targets`: UUID `id` with `gen_random_uuid()` default; UUID `owner_id` FK to `auth.users.id` with index; `name VARCHAR(120)`; `platform VARCHAR(32)` restricted to `google_maps`; `source_url TEXT`; `created_at TIMESTAMPTZ DEFAULT now()`. Its SQLAlchemy model uses a non-native enum with a check constraint. These fields do not themselves implement authorization or URL/input validation.

### Ownership rules to preserve in every future feature

- Derive ownership from `CurrentUser.id`, never request body/query/header owner identifiers.
- Scope list queries on the backend. Never return all users' targets and filter in JavaScript.
- Authorize the parent target before reading or writing reviews, running ingestion, or performing another child operation.
- Knowing a UUID does not grant access. Check both the resource identifier and authenticated ownership.
- Denied operations must leave records unchanged and must not start provider processing.
- Keep authorization/not-found UI indistinguishable so another user's target is not disclosed.
- In future Q&A, restrict retrieval, prompts, caches, and responses to the authorized active target.
- Test with two distinct users and targets. Authentication success alone does not establish tenant isolation.
- Do not assume Supabase RLS exists or protects direct SQLAlchemy access. No RLS policy is committed on main or in the inspected target migration; the RLS/backend enforcement decision remains unresolved in PR #24.

### Target validation baseline

The UI document calls for a trimmed name of 1–120 characters and a valid HTTPS Google Maps business URL. Listed source forms include `www.google.com/maps/...`, `google.com/maps/...`, `maps.google.com/...`, `maps.app.goo.gl/...`, and `goo.gl/maps/...`.

Validate at the authoritative backend boundary and mirror errors in the UI. Test missing name, missing source, malformed input, and valid input. When implementing host checks, parse URLs and compare allowed hosts/path rules; do not use a substring match that accepts lookalike domains. Resolve provider/redirect behavior separately from basic input validity.

### Ingestion flow to implement

1. Authenticate the request and authorize its existing target.
2. Validate required source information before starting work.
3. Record the attempt separately from persisted reviews.
4. Obtain real representative review records through a documented provider/import adapter.
5. Normalize text and rating; preserve optional source ID, reviewer name, date, review URL, and useful metadata.
6. Handle malformed records consistently without corrupting valid data; missing text and missing/invalid ratings need explicit tests.
7. Persist normalized reviews under the correct target with explicit transaction/error handling.
8. Record and return the actual result. Show safe errors, retain previously valid reviews, and log diagnostic information without secrets.

Never silently replace failed ingestion with sample reviews. Tests should use deterministic fixtures/mocks, not depend entirely on Google Maps or a live provider. Duplicate source identifiers are worth preserving, but sophisticated deduplication/re-ingestion is not a Sprint 1 requirement.

The UI vocabulary is no run → **Not ingested**, `processing` → **Ingesting**, `succeeded` → **Ingested**, optional `partial` → **Partially ingested**, `failed` → **Failed**. Counts and statuses must come from persisted backend results. Detailed analytics belong to Sprint 2.

CSV column names (`rating`, `review_text`), file size limits, review caps, provider choice, and sync/async execution details are not finalized implemented contracts. Keep them explicit when implementing #20/#21/#23 instead of silently treating UI examples as a completed API specification.

## 7. Local setup and configuration

Run backend commands **inside `backend/`**: Pydantic reads `.env` relative to the working directory. Frontend commands run inside `frontend/`. Use separate terminals.

### Backend (Linux/macOS/WSL)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
# Fill in local configuration, then:
uvicorn app.main:create_app --factory --reload --port 8000
```

On Windows PowerShell, the README uses `py -3.13 -m venv .venv`, `.\.venv\Scripts\Activate.ps1`, and `Copy-Item .env.example .env`. Use Python 3.12+ from a supported installation; the README excludes MSYS2/MinGW Python for Ruff installation.

### Frontend (second terminal, from repository root)

```bash
cd frontend
npm ci
cp .env.example .env
# Fill in public configuration, then:
npm run dev
```

Frontend normally serves at `http://localhost:5173`, backend at `http://localhost:8000`, local Swagger at `http://localhost:8000/docs`. If changing the backend port, update `VITE_API_BASE_URL`; if changing the frontend origin, update CORS and Supabase redirect configuration.

Use `npm ci` for a reproducible existing checkout. `npm install` is the README's first-install command and is appropriate when intentionally changing dependencies; review and commit resulting lockfile changes.

### Backend environment

| Variable | Requirement/behavior |
| --- | --- |
| `ENVIRONMENT` | `local` (default), `test`, or `production` |
| `DATABASE_URL` | Required secret PostgreSQL connection string; stored as Pydantic SecretStr |
| `CORS_ORIGINS` | Required non-empty comma-separated frontend origins |
| `SUPABASE_URL` | Required project URL; issuer/JWKS derived from it |
| `SUPABASE_PUBLISHABLE_KEY` | Required public publishable/anon key used in server session checks; `sb_secret_` rejected |
| `REVIEW_PROVIDER_API_KEY` | Future server-side secret placeholder for #20; not read by Settings yet |
| `REVIEW_MAX_PER_RUN` | Future cap placeholder for #20; not read by Settings yet |

### Frontend environment

| Variable | Purpose |
| --- | --- |
| `VITE_API_BASE_URL` | FastAPI base URL, without `/api` suffix |
| `VITE_SUPABASE_URL` | Public Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Public anon/publishable key only |

All three are required. Every `VITE_*` variable is potentially browser-visible. The config guard examines all string-valued `VITE_*` settings for `sb_secret_` keys and JWTs whose role is `service_role`; this is not a general-purpose secret scanner. Backend key validation currently only checks the `sb_secret_` prefix, so do not infer equivalent legacy service-role rejection there.

Never commit real `.env` files, credentials, passwords, provider/LLM secrets, or tokens. Keep `.env.example` in sync with configuration changes. Do not log raw tokens or database URLs; safe client messages and redacted technical logging are separate concerns.

### Supabase setup

Use the team's project; enable the Email auth provider and configure email confirmation. Set the local Site URL and allowed redirect URLs, including deployment URLs when applicable. Use asymmetric ECC/RSA signing keys compatible with the backend's allowed JWT algorithms. Copy public keys into the public-key settings and the database connection string into backend configuration only. No production credentials were inspected or tested during this research.

### Migrations

Add ordered SQL files such as `0001_create_analysis_targets.sql` to `backend/migrations/`. Never edit an already-applied shared migration; add another. Apply with the Supabase SQL Editor or an explicitly configured `psql` session according to the migration README. A value in backend `.env` is not automatically exported to a shell running `psql`.

Do not auto-apply migrations as part of a documentation or code-inspection task. Test PostgreSQL-specific schema behavior against PostgreSQL; SQLite cannot establish equivalence for cross-schema auth FKs, server defaults, or timezone handling.

## 8. Engineering conventions and UI standards

Follow the existing layer boundaries. Add routes under `backend/app/api/` and register them in `create_app`; keep authentication in the shared dependency/verifier. Keep source-specific ingestion parsing separate from UI and persistence. Do not invent a service/repository framework simply because one is common elsewhere.

Python uses snake_case modules/functions, PascalCase classes, typed interfaces, Ruff E/F/I rules, 88-character lines, and the Ruff formatter targeting Python 3.12. Frontend uses typed function components, PascalCase component/page files, camelCase utilities, type imports, single quotes, and no semicolons in existing source. oxlint checks React/TypeScript/Oxc rules, with hooks errors and component-export warnings. There is no committed frontend formatter command on main; do not claim Prettier enforcement exists.

Keep API calls in `frontend/src/lib/api/`, shared messages in `messages.ts`, auth behavior in `lib/auth/`, shared components in their existing folders. Extend reusable components instead of adding duplicate page-specific variants. Review dependency/API choices against authoritative documentation when changing integrations; retain the project's resolved versions unless the task needs an update.

Read the complete UI/UX context document for any screen change. Essential conventions:

- Calm analytics-oriented layout; analysis workspace is the central screen.
- Target name, Google Maps badge, source, and ingestion status remain visible on target-scoped screens.
- Desired shell: 56px header, 240px desktop sidebar, 1200px main maximum; desktop/tablet/mobile padding 32/24/16px. Auth forms use a centered 400px card.
- Use CSS tokens, including primary indigo `--color-primary`; do not hard-code component colors. Inter/system sans; body 14/20, H1 24/32, H2 20/28, H3 16/24. Spacing scale: 4, 8, 12, 16, 24, 32, 48, 64px.
- One H1 per page; sentence-case, verb-first actions; one primary action per region. Buttons perform actions; links navigate.
- Persistent labels, required markers, helper/error text, `aria-invalid` and `aria-describedby`; client and backend validation; focus the first invalid field. Preserve non-password input on failure.
- Explicit loading, empty, success, and error states; disable submitting actions; keep existing reviews visible after a failed ingestion.
- Never render raw Supabase/FastAPI/SQL errors or exception messages. Map errors to shared copy. Render review text as text, never raw HTML.
- Status uses text as well as color. Keyboard operation, visible focus, semantic controls, reduced-motion support, and appropriate focus management are required.
- Check UI at 1280px, 768px, and 375px widths. Follow the document's UI PR checklist.
- Reuse documented terms: Analysis target, Dashboard, Analysis workspace, Ingest reviews, Upload a CSV, Google Maps, Log in/Log out/Register.

The standards describe a destination, not the current component inventory: sidebar, toast provider, dialogs, target cards, status badges, URL fields, review lists, and workspace tabs remain to be built. Existing `TextField` supports only text/email/password, not URL or blur callbacks; existing `Alert` supports danger/success/info, not warning. Implement needed capabilities deliberately.

## 9. Tests, quality commands, and CI

### Backend checks (from backend with virtualenv active)

```bash
python -m ruff check .
python -m ruff format --check .
python -m compileall -q app tests
python -c "from app.main import create_app"
python -m pytest -ra
```

The import/build smoke check does not start the app or prove external configuration works. Focused examples: `python -m pytest tests/test_auth.py` and `python -m pytest tests/test_session_checker.py`.

### Frontend checks (from frontend)

```bash
npm run lint
npm run build
npm test
```

Build runs `tsc -b && vite build`; tests run `vitest run`. `npm run test:watch` is available for iteration. There is no `npm run typecheck`, root test command, or browser end-to-end suite on main.

### Existing coverage and boundaries

- Backend fixtures generate EC-signed test JWTs, inject a static JWKS source and fake session checker, and isolate settings from environment variables.
- Auth tests cover valid identity, missing/malformed/expired tokens, wrong claims/signing keys, unknown key ID, rejected HS256, spoofed client identity, remote outage, simulated logout, and rejection before contacting the provider.
- Session-checker tests mock `urllib.request.urlopen` and cover outbound headers, remote rejection, server failure, DNS/network failure, and timeout.
- Health tests override `get_db`; they check successful/failed database responses and CORS, not a real PostgreSQL connection.
- Config tests cover required values, allowed environments, database secret masking, URL conversion, and frontend secret-key guards.
- UI tests use MemoryRouter, fake Supabase auth, and mocked fetch for routing, login, registration, validation, password reveal, logout, session changes, and safe error mapping.
- No main-branch tests yet prove target/review tenant isolation, real ingestion, real migrations, or a live Supabase session lifecycle.

For domain work, add behavioral tests for both success and failure, two-user isolation, rejected mutations leaving state unchanged, correct target association, malformed records, and failed ingestion preserving existing reviews. Keep provider calls deterministic in ordinary unit tests.

### CI and merge policy

CI triggers on every pull request, pushes to `main`, and manual dispatch. Jobs are named **Frontend**, **Backend**, and **Secrets**. It uses Node 22/Python 3.12, cancels superseded runs per ref, and has read-only contents permission.

Secrets checks reject tracked `.env` files other than `.env.example` and scan full history with checksum-verified gitleaks 8.30.1. Removing a secret in a later commit does not remove exposure; rotate it and follow history remediation practices.

The README requires PRs, successful required checks, up-to-date branches, and no bypass. However, the inspected GitHub branches response reported **`main.protected = false`**. Treat merge enforcement as a configuration gap to verify, not a guarantee supplied by the CI YAML. Do not change repository settings as an incidental implementation action.

Verified remote evidence: [CI run 41169689439](https://github.com/varshanarayanann/ReviewLensAI/actions/runs/41169689439) for the inspected main SHA completed successfully, including all three jobs. This is historical remote evidence, not a new local test run. During this documentation task no application suites were rerun; Node was unavailable in the shell, and no live Supabase/database/provider integration was exercised.

## S1-019 handoff update (2026-11-02, branch work)

The independent ingestion handoff retains the current CSV source mechanism.
`read_csv_source` runs only after parent authorization and rejects missing or
unusable CSV structure before an attempt is recorded. Requests accept only
`csv_text`; required headers, 1–1,000 records, and a 1,000,000 UTF-8 byte limit
are documented in [the CSV contract](docs/csv-import-format.md). Normalization
failures still produce recorded failed runs, while source rejection changes no
stored records. See [the handoff](docs/handoffs/s1-019-ingestion.md) for branch
provenance and S1-018 integration notes. No new PR is created by this handoff,
and primary URL/provider collection remains separate work.

## 10. Full Sprint 1 work map

Board snapshot: **23 items**, all visible groups fully paginated: Backlog 10, Ready 0, In progress 4, In review 3, Done 6. Story number matches issue number in this snapshot. Read the full issue/CSV body for acceptance criteria; this table summarizes responsibility and outcome.

| Story / issue | Outcome | Assignee | Board state |
| --- | --- | --- | --- |
| [S1-001](https://github.com/varshanarayanann/ReviewLensAI/issues/1) | Engineering coding standards context | varshanarayanann | Backlog |
| [S1-002](https://github.com/varshanarayanann/ReviewLensAI/issues/2) | UI/UX standards context | amreenbhatia1 | Done |
| [S1-003](https://github.com/varshanarayanann/ReviewLensAI/issues/3) | Data/security guardrails context | JasmineG8493 | In review |
| [S1-004](https://github.com/varshanarayanann/ReviewLensAI/issues/4) | AI-assisted development/review context | bhavss05 | Done |
| [S1-005](https://github.com/varshanarayanann/ReviewLensAI/issues/5) | Structure and repeatable local workflow | amreenbhatia1 | Done |
| [S1-006](https://github.com/varshanarayanann/ReviewLensAI/issues/6) | Quality, formatting, automated test tooling | bhavss05 | Done |
| [S1-007](https://github.com/varshanarayanann/ReviewLensAI/issues/7) | PR CI and merge gate | amreenbhatia1 | In review |
| [S1-008](https://github.com/varshanarayanann/ReviewLensAI/issues/8) | Environment and secret management | amreenbhatia1 | Done |
| [S1-009](https://github.com/varshanarayanann/ReviewLensAI/issues/9) | Managed authentication | amreenbhatia1 | Done |
| [S1-010](https://github.com/varshanarayanann/ReviewLensAI/issues/10) | Protect frontend routes and backend operations | nidhisakpal | In progress |
| [S1-011](https://github.com/varshanarayanann/ReviewLensAI/issues/11) | Assign ownership from verified identity | varshanarayanann | Backlog |
| [S1-012](https://github.com/varshanarayanann/ReviewLensAI/issues/12) | Deny cross-user target read/mutation | bhavss05 | In progress |
| [S1-013](https://github.com/varshanarayanann/ReviewLensAI/issues/13) | Deny cross-user reviews/ingestion | varshanarayanann | Backlog |
| [S1-014](https://github.com/varshanarayanann/ReviewLensAI/issues/14) | Persist AnalysisTarget and owner relation | JasmineG8493 | In review |
| [S1-015](https://github.com/varshanarayanann/ReviewLensAI/issues/15) | Create target through UI | bhavss05 | Backlog |
| [S1-016](https://github.com/varshanarayanann/ReviewLensAI/issues/16) | Authoritative target input validation | nidhisakpal | In progress |
| [S1-017](https://github.com/varshanarayanann/ReviewLensAI/issues/17) | List only my targets | varshanarayanann | Backlog |
| [S1-018](https://github.com/varshanarayanann/ReviewLensAI/issues/18) | Open target workspace with explicit context | JasmineG8493 | Backlog |
| [S1-019](https://github.com/varshanarayanann/ReviewLensAI/issues/19) | Authorize and submit ingestion | JasmineG8493 | Backlog |
| [S1-020](https://github.com/varshanarayanann/ReviewLensAI/issues/20) | Extract/import real source reviews | varshanarayanann | Backlog |
| [S1-021](https://github.com/varshanarayanann/ReviewLensAI/issues/21) | Normalize review text/rating/metadata | JasmineG8493 | Backlog |
| [S1-022](https://github.com/varshanarayanann/ReviewLensAI/issues/22) | Persist reviews with target ownership | bhavss05 | Backlog |
| [S1-023](https://github.com/varshanarayanann/ReviewLensAI/issues/23) | Record and display ingestion result | nidhisakpal | In progress |

A useful implementation dependency order (inferred from acceptance criteria, not an official schedule) is auth/protection → target model/ownership/validation → target create/list/workspace → authorized ingestion → extraction/normalization → persistence/result reporting. Cross-user tests must accompany each new data boundary rather than being postponed until the end.

Business-rule references group around auth (S1-BR-001–006), ownership (007–010), secrets (011), targets (012–017), authorized ingestion (018–019), normalization/persistence (020–022), and outcomes/failure handling (023–026). The UI document additionally references 027 for CSV recovery. These are a navigation aid, not a reconstructed canonical rules document.

## 11. Branches, PRs, and unmerged work

| Ref / PR | Observed contents and implications |
| --- | --- |
| `main` at `aeb68cc` | Inspected working baseline |
| `Amreens-branch` at `fbc4857` | Auth/foundation work incorporated by merged PRs #25 and #26 |
| [PR #24](https://github.com/varshanarayanann/ReviewLensAI/pull/24), `Jasmine-branch` at `df520bb` | Open; proposes `docs/context/data-security-guardrails.md`. Covers ownership, secrets, cross-user tests, AI context isolation. Some decisions/config descriptions remain provisional |
| [PR #27](https://github.com/varshanarayanann/ReviewLensAI/pull/27), `S1-014-analysis-target` at `f926601` | Open; model, first SQL migration, two persistence tests. PR reports 44 backend tests passing; SQLite tests do not verify real PostgreSQL migration/auth schema |
| `Bhavyaa-branch` at `dd66e66` | Unmerged S1-004/S1-006 work: `AI_ASSISTED_DEVELOPMENT.md`, `DEVELOPMENT.md`, root pytest/Ruff config, extracted `scripts/import_sprint_issues.py`, five importer tests, simplified importer workflow. No corresponding PR in the inspected PR list |

The Bhavyaa branch derives from an earlier base and does not contain the current application tree. Its `DEVELOPMENT.md` says the importer is the only executable code; that is branch-local historical context, not today's main architecture. When integrating, preserve the newer frontend/backend files and CI. Reconcile overlapping `.gitignore` and importer workflow changes; add root tooling checks to CI without replacing application checks.

The branch-only AI policy names Copilot as default, describes review/dependency validation, requires test evidence and AI-session disclosure/retention with a PR, and calls for additional review on security-sensitive changes. It is not merged policy on main at this snapshot. The user's explicit authorization for the current tool/task governs this session; do not use that draft to demand redundant approval. If adopting the document, retain the project context and update stale assumptions rather than silently treating it as already integrated.

Do not merge or cherry-pick teammates' work merely to make documentation match. Recheck PR status and coordinate changes touching the same files.

## 12. Issue-import automation

`Import Sprint Issues` is a manual workflow with `csv_path` defaulting to `Sprint1Issues.csv` and `dry_run` defaulting to true. It requires CSV columns `story_id,title,body,labels,sprint`, handles UTF-8 BOM, reads comma-separated labels, paginates existing issues/labels, excludes PRs, skips exact existing titles, creates missing labels/issues when not dry-running, and writes a workflow summary.

Its permissions are `contents: read` and `issues: write`; it uses the workflow's GitHub token. It does not implement review ingestion, automatically assign team members, or add issues to the project board. The `sprint` column is required input but not separately converted into a milestone/project field. Renaming an issue title can bypass exact-title duplicate detection. Do not run the importer against GitHub unless issue creation is part of the requested task.

## 13. Known gaps and agent working checklist

Before implementing a story:

1. Read current git status, the active story/CSV requirements, relevant context, and affected tests. Recheck open PRs and branch-only work for overlap.
2. Distinguish required new behavior from existing implementation. Target/review/ingestion endpoints and tenant isolation are not already available just because the README describes them.
3. Preserve verified identity, backend ownership checks, safe user errors, real-data behavior, and deterministic test boundaries.
4. Make a focused change, update configuration examples/docs when contracts change, and run relevant quality checks. Report unrun checks and external integration limits accurately.
5. Review the complete diff and provide concrete test evidence in the PR. Include AI assistance disclosure/transcript or a sanitized prompt-and-verification summary when following the branch AI-review policy. Do not commit raw session logs by default.
6. Update this guide's snapshot and implemented/planned distinctions when work merges. Do not alter board states, close issues, publish, or change deployment settings as an incidental documentation action.

Key unresolved items to keep visible:

- Engineering standards #1 have no dedicated document on main; this guide summarizes observed conventions without claiming that story was approved or closed.
- Done stories #4/#6 have branch-only artifacts; application lint/tests exist on main, but root importer tests/AI policy do not.
- #7 CI exists and passes historically, while merge protection was reported disabled.
- #10 has baseline dashboard and `/api/me` protection; future domain routes still require protection and tests.
- No target/review/run schema on main; PR #27 still needs real PostgreSQL verification.
- No selected provider adapter, review normalization/persistence, complete CSV schema, ingestion caps, or run-processing implementation.
- No committed tenant RLS policy, cross-user domain tests, or proven live logout-token invalidation test.
- UI spec exceeds implementation: password reset, sidebar, target/workspace pages, shared UI inventory, responsive requirements, and several form behaviors remain unfinished.
- No verified live deployment or end-to-end system test.

Research basis: the complete tracked main source/config/test tree, all Sprint 1 issue bodies and CSV, public project board data (all 23 items), repository issue/PR metadata, the sole issue discussion on #20, both open PR diffs, all listed branch heads and relevant unique branch work, and the main-commit CI job results. Authenticated Projects API access lacked `read:project`; public board HTML supplied the board snapshot instead. No private course documents or live service configuration were assumed.

## Local implementation update (2026-11-01, unmerged)

The original main snapshot above predates the current local Nidhi changes. See
[docs/nidhi-ticket-status.md](docs/nidhi-ticket-status.md) for current delivery,
branch provenance, validation and outstanding dependencies. Local code now adds
protected target creation/read APIs, authoritative input validation, persisted
CSV ingestion runs/reviews, latest-result retrieval, and protected browser forms.
Primary URL ingestion and real PostgreSQL migration verification remain pending.


### S1-023 verification update (2026-11-02)

PR #28 is merged. Actual SQL migrations and ingestion outcome transactions now
have PostgreSQL integration coverage in `backend/tests/test_target_workflow.py`.
Set `TEST_POSTGRES_URL` to a disposable server with database-creation permission;
the tests create/drop isolated databases. Backend CI supplies PostgreSQL 18.
Hosted Supabase auth remains mocked; do not describe this as live Supabase testing.
S1-023 acceptance is satisfied by CSV ingestion results; primary URL-provider
integration remains S1-020 work, not an absolute prerequisite for S1-023 closure.

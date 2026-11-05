# ReviewLens AI

A multi-user Review Intelligence Portal (CS 490 capstone). Users create analysis
targets for Google Maps businesses, ingest their reviews, and (from Sprint 2) ask
questions grounded only in those reviews.

## Repository structure

Before modifying code, read the [Engineering Coding Standards](docs/context/engineering-coding-standards.md)
(S1-001). For screen changes, also follow the [UI/UX Standards](docs/context/ui-ux-standards.md).

| Path | Responsibility |
| --- | --- |
| `frontend/` | React + TypeScript single-page app (Vite). UI only; talks to the backend over HTTP. |
| `backend/` | Python FastAPI API: authentication checks, ownership rules, ingestion, persistence. |
| `backend/app/config.py` | All backend configuration, loaded from environment variables / `backend/.env`. |
| `backend/app/db.py` | Database connection (PostgreSQL on Supabase) and request-scoped sessions. |
| `backend/migrations/` | Version-controlled SQL migrations for the database schema. |
| `docs/` | Team context documents (UI/UX standards, design notes). |
| `.github/workflows/` | GitHub Actions: `ci.yml` (pull request checks), `import-sprint-issues.yml`. |

| Concern | Technology |
| --- | --- |
| Frontend | React, TypeScript, Vite, Vitest, oxlint |
| Backend | Python 3.12+, FastAPI, SQLAlchemy, pytest, Ruff |
| Database | PostgreSQL (Supabase) |
| Authentication | Supabase Auth |
| Deployment (Sprint 3) | Netlify (frontend), Render (backend) |

## Prerequisites

- **Node.js 22+** (includes npm)
- **Python 3.12+** from python.org. On Windows use the `py` launcher (`py -3.12` or `py -3.13`).
  The MSYS2/MinGW Python cannot install Ruff and is not supported.
- **Git**
- Access to the team's **Supabase project** (ask a teammate to invite you) for the
  database connection string and API keys.

## First-time setup

### 1. Backend

```powershell
cd backend
py -3.13 -m venv .venv                 # macOS/Linux: python3 -m venv .venv
.\.venv\Scripts\Activate.ps1           # macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env            # macOS/Linux: cp .env.example .env
```

Edit `backend/.env` and fill in the values (see [Environment variables](#environment-variables)).

### 2. Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env            # macOS/Linux: cp .env.example .env
```

Edit `frontend/.env` and fill in the Supabase values. Change `VITE_API_BASE_URL`
if your backend does not run on `http://localhost:8000`.

### 3. Supabase Auth

Accounts, passwords, and sessions are managed by Supabase Auth; ReviewLens never
stores passwords. One team member sets up the shared Supabase project:

1. **Authentication > Sign In / Providers > Email**: enable the Email provider.
   Keep **Confirm email** on (recommended) so new accounts must confirm their address.
2. **Authentication > URL Configuration**: set **Site URL** to
   `http://localhost:5173` for local development and add the deployed Netlify URL
   (for example `https://<site>.netlify.app/login`) to **Redirect URLs**.
3. **Project Settings > API Keys**: make sure the project uses the new
   asymmetric **JWT signing keys** (ECC or RSA). The backend verifies login tokens
   with the project's public keys at `/auth/v1/.well-known/jwks.json`, so it needs
   no Supabase secret.
4. Copy the values into your `.env` files:
   - `backend/.env`: `SUPABASE_URL` = the Project URL and
     `SUPABASE_PUBLISHABLE_KEY` = the publishable key.
   - `frontend/.env`: `VITE_SUPABASE_URL` = the Project URL and
     `VITE_SUPABASE_ANON_KEY` = the anon or publishable key.
     Never use the service-role or `sb_secret_` key.

## Running locally

Use two terminals.

**Terminal 1 - backend** (http://localhost:8000, API docs at http://localhost:8000/docs):

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:create_app --factory --reload --port 8000
```

**Terminal 2 - frontend** (http://localhost:5173):

```powershell
cd frontend
npm run dev
```

Open http://localhost:5173. Logged-out visitors land on **Log in**; use
**Register** to create an account. After logging in, the dashboard shows
**Logged in as &lt;your email&gt;**, which the backend confirms by verifying your
login token. **Log out** is in the header.

Quick checks:

- `GET http://localhost:8000/api/health` returns `{"status":"ok"}`.
- `GET http://localhost:8000/api/me` returns `401` without a login token, and
  `{"id": "...", "email": "..."}` with `Authorization: Bearer <access token>`.
- `GET http://localhost:8000/api/health/db` returns `{"database":"ok"}` when
  `DATABASE_URL` is correct, or `503 {"database":"unavailable"}` when it is not.

If port 8000 is already in use, start the backend with another port (for example
`--port 8001`) and set `VITE_API_BASE_URL=http://localhost:8001` in `frontend/.env`.

## Review and ingestion authorization (S1-013)

Review ownership is inherited through `AnalysisTarget.owner_id`. Every implemented
child operation authenticates the caller and checks the parent target by both ID
and verified owner before accessing review data or starting ingestion:

| Operation | Contract |
| --- | --- |
| `GET /api/targets/{target_id}/reviews` | Returns only that owned target's persisted reviews as a JSON array. Each record contains `id`, `target_id`, `run_id`, `review_text`, and `rating`. |
| `POST /api/targets/{target_id}/ingestions` | Creates reviews through CSV ingestion only after parent authorization. |
| `GET /api/targets/{target_id}/ingestions/latest` | Returns only the authorized target's latest ingestion result. |

Review listing uses UUID order for deterministic paging: `limit` defaults to 50
(1–100 allowed), and `offset` defaults to 0 (nonnegative). An owned target with no
reviews returns `[]`. Missing and inaccessible targets both return
`404 {"detail":"Analysis target not found."}`; missing/invalid authentication
returns 401. Identity/target query parameters do not override the authenticated
user or path target. Direct review creation, editing, and deletion endpoints are
not exposed; ingestion is the only implemented review-write operation.

Two-user regression tests in `backend/tests/test_target_workflow.py` verify reads,
ingestion denial before CSV processing, unchanged stored targets/reviews/runs
after denial, unavailable direct writes, and authentication requirements. They
run against SQLite and PostgreSQL using the existing disposable-database fixture.

## Quality checks

Run these before opening a pull request.

**Backend** (from `backend/`, with the virtual environment active):

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pytest --cov --cov-report=xml --cov-report=term
diff-cover coverage.xml --compare-branch=origin/main --fail-under=80
```

**Frontend** (from `frontend/`):

```powershell
npm run lint
npm run test:coverage
..\backend\.venv\Scripts\diff-cover.exe coverage\cobertura-coverage.xml --compare-branch=origin/main --fail-under=80
npm run build
```

Run `git fetch origin` before the `diff-cover` commands so they compare against
the current `main`.

## My analysis targets (S1-017)

The protected Dashboard loads `GET /api/targets` with the current bearer token.
The backend applies `AnalysisTarget.owner_id == CurrentUser.id` in its SQL query;
it never sends all users' targets to the browser for filtering. Identity headers
or query parameters cannot override the verified owner. Missing/invalid tokens
return 401, while an authenticated user with no targets receives `[]`.

The response is a JSON array containing `id`, `name`, `platform`, `source_url`,
and `created_at`, ordered newest first (UUID descending breaks timestamp ties).
It contains all of the current user's targets, without a hidden page limit.
Cards show the name, Google Maps platform, source reference, and created date;
selecting a card opens `/targets/:targetId`. Loading, empty, safe error/retry,
and expired-session states are implemented. Changing accounts or API configuration
remounts the list, and late responses from the previous account are ignored.

The list does not add target deletion, ingestion statistics, or workspace redesign.
Tests cover two-user persisted isolation on SQLite/PostgreSQL and dashboard
navigation, failures, and session changes using deterministic fixtures.

## Continuous integration

`.github/workflows/ci.yml` runs automatically on every pull request, on every push
to `main`, and on demand from the Actions tab. `Frontend` and `Backend` each run
lint, build, and unit tests for one part of the repo:

| Check | Lint | Build | Unit tests | Changed-code coverage (pull requests) |
| --- | --- | --- | --- | --- |
| `Frontend` | `npm run lint` (oxlint) | `npm run build` (TypeScript type check + Vite build) | `npm run test:coverage` (Vitest) | `diff-cover`, 80% of changed lines |
| `Backend` | `ruff check` + `ruff format --check` | `compileall` + import of `app.main` | `pytest --cov` | `diff-cover`, 80% of changed lines |

The coverage gate fails a pull request when fewer than 80% of the lines it adds or
changes are run by tests. See [Changed-code coverage gate](docs/coverage-gate.md)
for the policy, exclusions, and how to run it locally (S2-001).

`Secrets` fails if any `.env` file (other than `.env.example`) is committed, and
scans the full git history with [gitleaks](https://github.com/gitleaks/gitleaks)
for leaked keys, tokens, and passwords. If it fails, remove the secret **and
rotate it** in the provider's dashboard; deleting it from a later commit does not
remove it from history.

Any failing step fails its check. Open the failed check on the pull request to
see which step failed; Ruff problems are also annotated on the changed lines.

### Merge protection

`main` must be protected so pull requests cannot be merged while a check fails.
A repository admin sets this in **Settings > Branches > Add branch protection rule**
(or **Settings > Rules > Rulesets**) for `main`:

- Require a pull request before merging.
- Require status checks to pass before merging: `Frontend`, `Backend`, `Secrets`.
- Require branches to be up to date before merging.
- Do not allow bypassing the above settings.

A check name only appears in that list after the workflow has run once, so open
a pull request first. When new code areas are added (for example the repo tooling
in `scripts/` and `tests/` from S1-006), add their lint, build, and test steps to
`ci.yml` in the same pull request and mark any new job as required.

## Environment variables

Real values live only in `backend/.env` and `frontend/.env`, which are git-ignored.
The committed `.env.example` files list every required name. Never commit secrets.

### Backend (`backend/.env`) - server-side only

| Name | Required | Description |
| --- | --- | --- |
| `ENVIRONMENT` | No (default `local`) | `local`, `test`, or `production` |
| `DATABASE_URL` | Yes | **Secret.** Postgres connection string from Supabase Dashboard > Connect (Session pooler) |
| `CORS_ORIGINS` | Yes | Comma-separated frontend origins allowed to call the API, e.g. `http://localhost:5173` |
| `SUPABASE_URL` | Yes | Supabase project URL, e.g. `https://<project-ref>.supabase.co`. Used to fetch the public keys that verify login tokens |
| `SUPABASE_PUBLISHABLE_KEY` | Yes | Supabase publishable (or anon) key, the same public value as `VITE_SUPABASE_ANON_KEY`. Used to confirm with Supabase Auth that a login session is still active, so a token stops working as soon as its user logs out. The backend refuses an `sb_secret_` key here |
| `REVIEW_PROVIDER_API_KEY` | Future URL integration | Reserved server-side secret placeholder; not read by Settings or required for the S1-020 CSV import path |
| `REVIEW_MAX_PER_RUN` | Future URL integration | Reserved provider cap; current CSV imports use a fixed maximum of 1,000 records |

The backend refuses to start and names the missing variables if a required value is absent.
`DATABASE_URL` is stored as a secret value, so it prints as `**********` in logs and errors.

### Frontend (`frontend/.env`) - bundled into browser code

| Name | Required | Description |
| --- | --- | --- |
| `VITE_API_BASE_URL` | Yes | Backend base URL, e.g. `http://localhost:8000` |
| `VITE_SUPABASE_URL` | Yes | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Yes | Supabase anon or publishable (public) key. The app refuses to start if a service-role or `sb_secret_` key is put here |

Every `VITE_*` value is visible in the browser. Only public values belong here;
the Supabase service-role key and database password must never appear in the frontend.

## Review source import (S1-020)

ReviewLens obtains individual review text/rating records from user-supplied CSV
exports for an authorized Google Maps target. The pure adapter in
`backend/app/reviews/csv_source.py` handles CSV structure independently of the UI,
HTTP routes, and persistence; it preserves optional metadata for normalization.
Source rejection never inserts sample reviews or substitutes test fixtures.

See [the selected ingestion approach](docs/review-ingestion-approach.md) and
[CSV format](docs/csv-import-format.md) for limits, fixture provenance, and normalization
integration notes. This implements the issue's practical-import option;
automatic collection from the saved Google Maps URL still requires a separately
selected/configured provider integration. No provider key is needed for CSV.

## Ingestion source submission (S1-019)

The existing CSV import path submits JSON `csv_text` to
`POST /api/targets/{target_id}/ingestions` with the current bearer token. The
backend verifies target ownership before parsing, then checks required CSV
structure and limits before creating an attempt. Rejected sources return 422
without altering reviews or the previous latest result. Missing/cross-user
targets share the same 404 response and start no processing.

See [the CSV source contract](docs/csv-import-format.md) for exact columns, limits,
and outcome semantics, and [the S1-019 handoff](docs/handoffs/s1-019-ingestion.md)
for the original issue author's branch/PR instructions. Primary URL/provider
collection remains separate work; no provider credentials are needed for CSV.

## Database migrations

### Record ownership (S1-011)

`AnalysisTarget.owner_id` stores the verified Supabase user's JWT subject as a
UUID, referencing `auth.users.id`. `POST /api/targets` derives it from
`Depends(get_current_user)`; clients supply only the editable target fields.
Ownership fields such as `owner_id` or `userId` in the JSON body are rejected with
422. Query parameters and identity headers cannot override the verified subject.

Reviews and ingestion runs inherit ownership through their persisted target.
The backend checks target ID and owner before creating either child record;
another user's target returns 404 and creates no records. CSV requests accept
only `csv_text`, rejecting client-supplied ownership or association fields.
No separate application User table or duplicated child owner field is required.

Regression tests in `backend/tests/test_target_workflow.py` check persisted owners
for two signed identities, spoofed inputs, unauthenticated creation, and child
associations against SQLite and, when `TEST_POSTGRES_URL` is configured, PostgreSQL.

### Applying schema changes

Schema changes are SQL files in `backend/migrations/`, applied in filename order.
See `backend/migrations/README.md`.

## Analysis workspace (S1-018)

`/targets/:targetId` loads the authorized target and its latest recorded ingestion
result through FastAPI. The workspace displays the target name, Google Maps
platform, saved source URL, and current basic ingestion status. The protected
`GET /api/targets/{targetId}` response includes `id`, `name`, `platform`, and
`source_url`; inaccessible and missing targets both return 404.

Use **Upload a CSV** for the implemented ingestion path, then **Refresh workspace**
to reload the persisted result. CSV import uses the existing API and limits;
collection directly from the saved Google Maps URL remains provider-integration
work. Dashboard card selection is delivered separately by S1-017; direct links
and navigation after target creation work without it.

The original S1-018 author can integrate the completed feature and update her
existing draft PR using [the handoff instructions](docs/handoffs/s1-018-workspace.md).

## Review Q&A and its test harness (S2-003)

`POST /api/targets/{target_id}/questions` accepts `{"question": "..."}` and answers
from the authenticated owner's persisted reviews for that target only. Another
user's target returns the same 404 as a missing one, and a target with no reviews
returns `status: "no_reviews"` without calling the model.

No LLM provider is configured yet, so the running app returns 503 for questions.
Tests replace the model with a recording fake, so CI needs no API key. See
[the Q&A test harness](docs/qa-test-harness.md) for the model boundary, how to
write Q&A tests, and what a real provider adapter must do.

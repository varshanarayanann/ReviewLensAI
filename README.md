# ReviewLens AI

A multi-user Review Intelligence Portal (CS 490 capstone). Users create analysis
targets for Google Maps businesses, ingest their reviews, and (from Sprint 2) ask
questions grounded only in those reviews.

## Repository structure

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
   - `backend/.env`: `SUPABASE_URL` = the Project URL.
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

## Quality checks

Run these before opening a pull request.

**Backend** (from `backend/`, with the virtual environment active):

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pytest
```

**Frontend** (from `frontend/`):

```powershell
npm run lint
npm test
npm run build
```

## Continuous integration

`.github/workflows/ci.yml` runs automatically on every pull request, on every push
to `main`, and on demand from the Actions tab. `Frontend` and `Backend` each run
lint, build, and unit tests for one part of the repo:

| Check | Lint | Build | Unit tests |
| --- | --- | --- | --- |
| `Frontend` | `npm run lint` (oxlint) | `npm run build` (TypeScript type check + Vite build) | `npm test` (Vitest) |
| `Backend` | `ruff check` + `ruff format --check` | `compileall` + import of `app.main` | `pytest` |

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
| `REVIEW_PROVIDER_API_KEY` | From S1-020 | **Secret.** API key for the Google Maps review-data provider |
| `REVIEW_MAX_PER_RUN` | From S1-020 | Maximum reviews collected in one ingestion run |

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

## Database migrations

Schema changes are SQL files in `backend/migrations/`, applied in filename order.
See `backend/migrations/README.md`.

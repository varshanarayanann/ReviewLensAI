
# ReviewLens AI — Data and Security Guardrails

**Sprint 1 | S1-003**  
**Rules:** S1-BR-001 through S1-BR-011

## 1. Purpose and Authentication

ReviewLens allows multiple users to create AnalysisTargets and collect reviews. Since each user works with their own data, we must prevent one account from accessing another account's information. These guidelines apply to all developers and AI coding tools working on the application.

**Selected identity provider: Supabase Auth.** ReviewLens uses Supabase Auth to manage user authentication rather than building its own password storage or login system (S1-BR-001–002). The backend verifies bearer-token signatures and required claims against Supabase's public signing keys, then checks with Supabase Auth that the session is still active. These authentication and session checks are implemented in `backend/app/auth/` and are required for protected routes (S1-BR-003–004, 006). Logging out invalidates the session for backend requests. Authentication establishes identity; it does not by itself authorize access to a particular user's data. Cross-user ownership authorization must be verified through S1-012, S1-013, and their associated tests.

## 2. Identity and Data Ownership

After authentication, Supabase Auth provides a unique user identifier exposed to backend routes as `CurrentUser.id`. This verified identity maps directly to `AnalysisTarget.owner_id`; target ownership is derived from the authenticated user, not an owner ID submitted from the browser (S1-BR-005). The current implementation does not use a separate application User record.

The following records are user-scoped:

- **User:** The authenticated account.
- **AnalysisTarget:** The business or product being analyzed; each target has exactly one owner.
- **IngestionRun:** A review-collection attempt belonging to an AnalysisTarget.
- **Review:** A stored rating and review text associated with an AnalysisTarget, directly or through an IngestionRun.

Although reviews and ingestion runs may not store an owner ID directly, they must follow the ownership of their AnalysisTarget. Every user-owned record must remain associated with its authenticated owner (S1-BR-007).

## 3. Authorization and Prohibited Access

Authentication alone does not grant permission to access every record. The current implementation enforces ownership authorization through FastAPI backend queries using the verified `CurrentUser.id` (S1-BR-008–009). For example, when a user requests an AnalysisTarget, the query checks that the requested target belongs to the authenticated user. If ownership cannot be confirmed, the request must be denied. Do not rely on Supabase Row Level Security (RLS) as an enforcement layer unless it is separately verified and documented.

**Do not:**

- Trust a browser-supplied `user_id` or `owner_id` as proof of ownership (S1-BR-010).
- Fetch a target, review, or ingestion run by ID without verifying the related owner.
- Rely only on hidden frontend buttons or filtered pages for security.
- Allow ingestion, changes, or deletion of another user's target or reviews.
- Include another user's reviews in AI context, including after switching targets.

These restrictions are important because users can modify requests sent from their browser. Ownership must come from trusted authentication information, not client input.

## 4. Secrets and Environment Configuration

ReviewLens may use credentials for authentication, its database, review ingestion, and later AI services. Private API keys and credentials must not be committed to GitHub, included in frontend code, exposed to the browser, or printed in logs (S1-BR-011). Local values belong in ignored `backend/.env` and `frontend/.env` files; deployment secrets should use the hosting platform's protected configuration. The committed [`backend/.env.example`](../../backend/.env.example) and [`frontend/.env.example`](../../frontend/.env.example) document the established variable names with placeholders only. Only keys explicitly intended to be public may appear in frontend configuration. Exposed secrets must be revoked or rotated.

**Environment configuration:** Backend settings are validated by [`backend/app/config.py`](../../backend/app/config.py). The current backend variables are `ENVIRONMENT`, `DATABASE_URL`, `CORS_ORIGINS`, `SUPABASE_URL`, and `SUPABASE_PUBLISHABLE_KEY`. The example also reserves `REVIEW_PROVIDER_API_KEY` and `REVIEW_MAX_PER_RUN` for S1-020; they are not currently required by the settings model. Frontend variables are `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, and `VITE_SUPABASE_ANON_KEY`. Every `VITE_*` value is bundled into browser code: the Supabase URL and anon/publishable key are public, while database credentials and secret keys must remain backend-only. The README identifies Netlify and Render as planned deployment platforms; configure deployment values through their protected environment settings when deployed.

## 5. Cross-User Isolation Testing

To confirm that ownership is enforced, tests should use two accounts with separate targets and reviews:

| Scenario | Expected result |
| --- | --- |
| User A opens their own target | Allowed |
| User A lists targets | Only A's targets are returned |
| User A reads, changes, or deletes User B's target or reviews | Denied; B's data remains unchanged |
| User A tries to ingest reviews into B's target | Denied; no unauthorized records created |
| User A submits B's `owner_id` | Ignored as proof of ownership; unauthorized access denied |
| Unauthenticated request or invalidated session | Protected access denied |

These tests must verify backend behavior rather than relying only on what appears in the interface. Relevant automated tests should run locally and in pull-request CI, along with linting and build checks. The pull request must include a **Test Evidence** section describing actual results; tests should not be marked as passed unless they were run. When Q&A is added later, tests must also confirm that the model receives only the active user's authorized reviews.

## 6. Developer Checklist and Remaining Decisions

Before merging changes, developers and AI coding tools must verify authentication, enforce ownership on every user-owned operation, protect secrets, add appropriate negative-path tests, and confirm required CI checks pass. **Every query and mutation involving user-owned data must preserve user isolation.**

**Current implementation:** The verified Supabase subject is exposed to backend routes as `CurrentUser.id` and maps directly to `AnalysisTarget.owner_id`. FastAPI backend queries enforce ownership using that verified identity; a valid session alone is not proof of access to a target, review, or ingestion run. No claim is made here that Supabase Row Level Security (RLS) is enabled. Environment variable names and local conventions are established in the example files and backend settings; deployment configuration should follow the hosting platform's protected settings.

*References: Sprint 1 Stories (S1-003; S1-BR-001–011), ReviewLens Technical Specifications §3, Product Requirements Document §§4.1 and 7.*

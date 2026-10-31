
# ReviewLens AI — Data and Security Guardrails

**Sprint 1 | S1-003**  
**Rules:** S1-BR-001 through S1-BR-011

## 1. Purpose and Authentication

ReviewLens allows multiple users to create AnalysisTargets and collect reviews. Since each user works with their own data, we must prevent one account from accessing another account's information. These guidelines apply to all developers and AI coding tools working on the application.

**Selected identity provider: Supabase Auth.** ReviewLens will use Supabase Auth to manage user authentication rather than building its own password storage or login system (S1-BR-001–002). Authentication confirms a user's identity, while the backend verifies their credentials before allowing access to protected functionality. Supabase Auth will also manage user sessions, allowing users to remain logged in during normal navigation and page refreshes. Logging out must prevent the previous session from continuing to access protected functionality (S1-BR-003–004, 006).

## 2. Identity and Data Ownership

After authentication, Supabase Auth provides a unique user identifier that ReviewLens will use to associate the authenticated account with its application data. The FastAPI backend must verify the user's authentication token before using this identifier to determine which AnalysisTargets belong to them (S1-BR-005). If ReviewLens maintains a separate User record, it must be linked to the verified Supabase user ID. This allows ReviewLens to identify which AnalysisTargets belong to the user without relying on an owner ID submitted from the browser.

The following records are user-scoped:

- **User:** The authenticated account.
- **AnalysisTarget:** The business or product being analyzed; each target has exactly one owner.
- **IngestionRun:** A review-collection attempt belonging to an AnalysisTarget.
- **Review:** A stored rating and review text associated with an AnalysisTarget, directly or through an IngestionRun.

Although reviews and ingestion runs may not store an owner ID directly, they must follow the ownership of their AnalysisTarget. Every user-owned record must remain associated with its authenticated owner (S1-BR-007).

## 3. Authorization and Prohibited Access

Authentication alone does not grant permission to access every record. Before reading, creating, updating, deleting, or ingesting user-owned data, the backend or database security layer must verify ownership (S1-BR-008–009). For example, when a user requests an AnalysisTarget, the application must confirm that the requested target belongs to the user identified by the verified session. If ownership cannot be confirmed, the request must be denied.

**Do not:**

- Trust a browser-supplied `user_id` or `owner_id` as proof of ownership (S1-BR-010).
- Fetch a target, review, or ingestion run by ID without verifying the related owner.
- Rely only on hidden frontend buttons or filtered pages for security.
- Allow ingestion, changes, or deletion of another user's target or reviews.
- Include another user's reviews in AI context, including after switching targets.

These restrictions are important because users can modify requests sent from their browser. Ownership must come from trusted authentication information, not client input.

## 4. Secrets and Environment Configuration

ReviewLens may use credentials for authentication, its database, review ingestion, and later AI services. Private API keys and credentials must not be committed to GitHub, included in frontend code, exposed to the browser, or printed in logs (S1-BR-011). Local secrets should be stored in ignored environment files, while deployment secrets should use the hosting platform's protected configuration. An `.env.example` may list variable names with placeholder values. Only keys explicitly intended to be public may appear in frontend configuration. Exposed secrets must be revoked or rotated.

**Environment configuration:** Frontend environment variables will be configured through Netlify, while backend secrets will be stored in Render's environment settings. Local development will use environment files excluded from Git. The team must still confirm the specific variable names and configuration conventions.

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

**Implementation decisions to confirm:** The team should agree on how Supabase user identities map to application records, whether ownership checks will be enforced through FastAPI, Supabase Row Level Security (RLS), or both, and how environment variables will be configured. These decisions should be reflected in this document as implementation progresses.

*References: Sprint 1 Stories (S1-003; S1-BR-001–011), ReviewLens Technical Specifications §3, Product Requirements Document §§4.1 and 7.*

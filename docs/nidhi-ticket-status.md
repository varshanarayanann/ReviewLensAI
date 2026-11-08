# Nidhi ticket delivery — 2026-11-07

Current baseline: `main` at `df5ffc3`. Assigned open issues were verified through
GitHub on 2026-11-07. Changes are implemented on `nidhi/sprint2-review-context`
and await PR review/merge; GitHub issues remain open until merge.

| Ticket | Delivery |
| --- | --- |
| #55 / S2-010 | Complete persisted context with owner/target filtering, stable ordering, 1,000-row and 64,000-byte JSON limits; overflow fails before the model. |
| #57 / S2-012 | Explicit absent-versus-negative evidence instructions and a controlled parking-safety test against food/service reviews. |
| #61 / S2-016 | Same-client account transitions, spoofed owner inputs, direct helper filtering, and indistinguishable foreign/missing target errors tested at the model boundary. |
| #64 / S2-019 | Fresh column reads, immutable request context, stateless adapter contract, A → B → empty → A after failure, and committed update/deletion tests. |
| #10, #16, #23 | Already closed and implemented on main; existing backend regression coverage passed in this run. |

[Execution plan and research](qa-context-design.md) records the alternatives,
primary sources, architectural decision, limits and remaining provider/UI work.
`AGENTS.md` now starts with an authoritative current-state update; the old
research inventory below it is explicitly historical.

## Local verification

- Python 3.14.4, dependencies installed from committed backend manifests in a
  temporary virtual environment outside the repository; no manifest changes.
- Ruff check and format check passed (57 files).
- Compileall and application import smoke checks passed.
- Full backend suite: **262 passed, 97 skipped**. All skips are PostgreSQL
  variants because no disposable PostgreSQL server is configured locally.
- Backend changed-code coverage: **100%** (27 measured executable lines),
  above the required 80%; overall backend coverage 98%.
- `git diff --check` passed.
- No frontend code changes; local frontend tests were not rerun (Node absent).
  PR CI supplies Node 22, Python 3.12 and PostgreSQL 18 for full verification.
- No live Supabase or model calls, schema changes, deployments or secret changes.
  Mocked replies establish orchestration behavior, not live-model reliability.

## Publication blocker

Branch commits are local and reviewable. Publishing was attempted, but Git HTTPS
has no credentials in this environment and the connected GitHub integration
returned HTTP 403 (`Resource not accessible by integration`) for Git object
creation. No remote branch, PR, issue closure or CI run was created.

After restoring repository write access, publish with:

```bash
git push -u origin nidhi/sprint2-review-context
```

Open a PR into `main` referencing `Closes #55`, `Closes #57`, `Closes #61`, and
`Closes #64`, include this validation/AI assistance record, and obtain the
required human/security review. CI must verify PostgreSQL and frontend checks
before merge. Do not describe local implementation as merged delivery.

## AI assistance record

The user requested: “complete all the tickets assigned to nidhisakpal,” first
planning and researching implementation, then completing each ticket and updating
the agent guide. Codex assisted with issue/source inspection, primary-source
research, bounded context retrieval, evidence instructions, regression tests and
documentation. The diff was reviewed and the commands above were executed.
The PR must receive normal human review and additional security review under
`AI_ASSISTED_DEVELOPMENT.md` before merge. This sanitized task-and-verification
summary records the material assistance without retaining raw session logs.

---

## Historical Sprint 1 delivery record

The dated record below is retained for provenance; its branch states and blockers
are superseded by current source and the update above.

### Nidhi's Sprint 1 delivery and blockers

Updated 2026-11-02. Implementation PR #28 is merged into main. S1-010 and S1-016 are closed. S1-023 acceptance verification is complete for the implemented CSV ingestion path; see the verification addendum below.

## Branch research

Fetched all remote branches. Main remains aeb68cc. Bhavyaa-branch advanced to 1ba122f, incorporating main and AnalysisTarget persistence. Reused its three model files and 0001 SQL migration verbatim, matching the model in S1-014-analysis-target / PR #27. Jasmine-branch still contains security documentation; Amreens-branch contains merged auth work. No inspected branch contains target creation, review ingestion, or review persistence APIs.

## S1-010: implemented for current routes

Existing frontend guards and verified backend identity are reused. Added regression coverage enumerating API operations and requiring security plus safe anonymous rejection. New creation/workspace routes are nested under ProtectedRoute; target, import and result APIs independently require authentication. Target access additionally filters by verified owner. No client owner IDs are accepted.

## S1-016: integrated

AnalysisTargetCreate now validates the real POST /api/targets boundary. Name is trimmed, required and limited to 120 characters. Google Maps URLs require HTTPS and allowed parsed hosts/paths; credentials, unusual ports, malformed inputs and lookalike domains fail. Browser creation form submits to this endpoint, preserves input on rejection and displays a safe validation message. A dashboard link opens /targets/new, then successful creation navigates to the target workspace.

## S1-023: integrated for CSV recovery imports

POST /api/targets/{target_id}/ingestions accepts JSON {csv_text: string}. GET /api/targets/{target_id}/ingestions/latest restores the most recent recorded result. Both authorize the target first. The workspace displays target name/source and a CSV picker, loading state, safe success/failure messages, and restored results.

IngestionRun is committed before processing. Reviews and successful outcome commit together. Failure rolls back new reviews and records failed state in a fresh transaction; existing reviews are untouched. Diagnostic logs contain run ID and exception class, not CSV contents, driver parameters or secrets. Tests inject a write failure to verify this behavior. Database failure preventing even the attempt/failure record from being committed remains an infrastructure error, not a fabricated success.

CSV contract: UTF-8 text, optional BOM, required rating/review_text headers, integer ratings 1–5, nonblank text, at most 1,000 reviews and 1,000,000 text characters (browser additionally limits file bytes). Any invalid record rejects the whole attempt. No partial-success semantics or duplicate detection. Counts represent committed reviews. Synchronous requests expose final outcomes; processing is persisted while execution is underway. This is real import, not sample-data substitution.

## Remaining blockers / limitations

- S1-020 (varshanarayanann): primary URL/provider ingestion is absent from all inspected branches. This delivery implements the documented CSV recovery path, not primary URL ingestion. Connect provider extraction/normalization to the same outcome transaction boundary when available.
- S1-014: upstream model is still unmerged. Local integration reuses it; do not merge competing copies or renumber migrations without coordinating with Jasmine/Bhavyaa.
- S1-018/021/022: supporting minimal workspace/CSV parser/review storage were necessary to exercise these tickets. Coordinate these interfaces with their owners before merging; the full review-list/dashboard experience and provider metadata handling are not delivered here.
- PostgreSQL migration/workflow verification is now covered by automated tests applying the actual SQL migrations. Hosted Supabase configuration has not been exercised; tests create only the auth.users key needed by the migration.
- No live Supabase logout/revocation or live provider testing performed.
- Workspace uses a safe form-level validation summary; complete field-specific UI error mapping and broader UX specification compliance remain follow-up work.
- No scheduler/recovery of processing runs after process termination; no retry/deduplication policy.

## Validation

Backend: 76 tests passed, Ruff check passed. Tests cover target validation, authenticated creation, CSV success/failure, old-review preservation, cross-user read/write denial, and injected persistence failure. Test DB uses SQLite with an attached auth schema; this is not PostgreSQL migration coverage.

Frontend: temporary checksum-verified Node 22 runtime installed outside repository; npm ci succeeded. Frontend lint passed with one non-blocking set-state-in-effect warning. Production build passed. All 34 frontend tests passed across three files in a temporary Linux-directory copy of the same source and lockfile. The initial Windows-mount run timed out starting workers; the single-thread retry stalled and was stopped. No dependency manifests or lockfile were intentionally changed.

## Run locally

Follow README environment setup. Apply backend/migrations/0001_create_analysis_targets.sql and 0002_create_ingestion_runs_and_reviews.sql to the intended test database before using new features. Start frontend and backend; log in, choose New target, create a Google Maps target, then upload a CSV with rating and review_text columns. Reload the workspace to verify recorded state. Try a malformed CSV after a successful import to verify a safe failure; existing persisted reviews should remain.


## S1-023 acceptance verification (2026-11-02)

The ticket requires recorded outcomes and user-visible confirmation/error handling; it does not require a URL provider. The earlier claim that S1-020 was an absolute prerequisite for closing S1-023 was too broad. URL ingestion remains separate provider integration work and does not invalidate the verified CSV result-handling path.

A temporary unprivileged PostgreSQL 18.6 server verified the real SQL migrations and application workflow. Each test creates its own uniquely named database, supplies a minimal auth.users table (the Supabase-owned FK target), applies committed migrations in filename order, and removes only that test database afterward. No hosted Supabase project or existing application data was touched.

Acceptance evidence:
- Attempts are recorded separately in ingestion_runs.
- Successful CSV imports persist reviews and report the committed count.
- Invalid input records a safe failed outcome; previous reviews remain intact.
- Latest-result retrieval through a new request returns the recorded outcome.
- PostgreSQL transaction failure is followed by rollback and a committed failed attempt.
- Failure logging contains run ID/exception class, not SQL or sensitive diagnostics.
- Other users cannot initiate ingestion or retrieve the result.
- Existing frontend tests verify safe result display; previous frontend CI passed.

Backend validation: 78 tests passed with PostgreSQL enabled (SQLite and PostgreSQL workflow variants); Ruff check/format passed. CI now provisions PostgreSQL 18 and runs these same integration cases. Tests without TEST_POSTGRES_URL skip the two PostgreSQL variants, not the SQLite cases.

To reproduce: point TEST_POSTGRES_URL at a disposable PostgreSQL server using a role allowed to create databases, then run `python -m pytest -ra` from backend. This variable is distinct from the application DATABASE_URL. Never use production credentials. The fixture creates/drops only its own random database; existing databases are not migrated or cleared.

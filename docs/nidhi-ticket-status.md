# Nidhi's Sprint 1 delivery and blockers

Updated 2026-11-01. Local changes; no remote tickets closed or branches merged.

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
- Real PostgreSQL/Supabase migration verification remains pending. Apply 0001 then 0002 in a designated test database. SQLite tests exercise the ORM/API transaction flow, not PostgreSQL-specific auth-schema/default behavior.
- No live Supabase logout/revocation or live provider testing performed.
- Workspace uses a safe form-level validation summary; complete field-specific UI error mapping and broader UX specification compliance remain follow-up work.
- No scheduler/recovery of processing runs after process termination; no retry/deduplication policy.

## Validation

Backend: 76 tests passed, Ruff check passed. Tests cover target validation, authenticated creation, CSV success/failure, old-review preservation, cross-user read/write denial, and injected persistence failure. Test DB uses SQLite with an attached auth schema; this is not PostgreSQL migration coverage.

Frontend: temporary checksum-verified Node 22 runtime installed outside repository; npm ci succeeded. Frontend lint passed with one non-blocking set-state-in-effect warning. Production build passed. All 34 frontend tests passed across three files in a temporary Linux-directory copy of the same source and lockfile. The initial Windows-mount run timed out starting workers; the single-thread retry stalled and was stopped. No dependency manifests or lockfile were intentionally changed.

## Run locally

Follow README environment setup. Apply backend/migrations/0001_create_analysis_targets.sql and 0002_create_ingestion_runs_and_reviews.sql to the intended test database before using new features. Start frontend and backend; log in, choose New target, create a Google Maps target, then upload a CSV with rating and review_text columns. Reload the workspace to verify recorded state. Try a malformed CSV after a successful import to verify a safe failure; existing persisted reviews should remain.

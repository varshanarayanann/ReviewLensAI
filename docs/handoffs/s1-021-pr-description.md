## Changes

Completes S1-021 (S1-BR-020, S1-BR-021, S1-BR-024) by connecting the existing pure
normalizer to the S1-020 raw-source adapter before ORM Review creation/persistence.

- Require trimmed nonblank text and canonical whole-number ratings 1–5; reject
  missing/invalid values without mutating other normalization candidates.
- Preserve optional source ID, reviewer, date, URL, and unknown JSON-safe metadata
  without inventing missing values or allowing metadata to control ownership.
- Persist metadata in a new JSONB object column, defaulting existing rows to `{}`,
  through ordered migration 0003. Earlier applied migrations are unchanged.
- Keep the current all-or-nothing HTTP import contract: any rejected record fails
  that recorded batch; no new rows are committed and previous reviews remain intact.
- Add end-to-end adapter/normalizer/database, mixed-record, metadata, association,
  and actual PostgreSQL migration tests. Document the canonical and rejection policy.

## Dependency

Depends on **S1-020 PR #39**. Keep this PR in draft until #39 merges, update this
branch from main, rerun checks, and verify this diff no longer bundles the upstream
adapter work. The original normalizer and author history are preserved.

## Validation

- Full backend suite: **150 passed, zero skipped**, on SQLite and disposable local
  PostgreSQL 18.6, including the actual metadata migration against an existing row,
  its JSONB object constraint, and source/normalizer/persistence round-trips.
- Frontend: **35 tests passed**; lint and production build passed. The existing
  TargetWorkflowPage set-state-in-effect lint warning remains; S1-021 adds no UI code.
- Ruff lint/format, compileall, application import, documentation links, and final
  whitespace checks passed. The temporary PostgreSQL server was stopped afterward.
- No shared Supabase migration or live provider call was performed.

## Scope

No URL provider, Summary/Ask features, new frontend behavior, or new dependency.
The pure normalizer reports individual rejection reasons; partial persistence and
new ingestion status contracts are not introduced. Metadata URLs are stored as
untrusted source values, not fetched. Hosted Supabase Auth/provider calls are mocked.

Closes #21

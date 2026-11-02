## Changes

Completes S1-019 (S1-BR-018, S1-BR-019, S1-BR-025) using the existing practical
CSV import path for Google Maps review data.

- Verify authentication and existing target ownership before CSV parsing.
- Reject unexpected ownership/association fields, missing source input, and
  unusable CSV structure before recording an ingestion attempt.
- Require rating/review_text columns, unique headers, 1–1,000 records, and at most
  1,000,000 UTF-8 source bytes; handle BOM and malformed CSV safely.
- Preserve existing normalization/persistence outcomes for accepted sources and
  retain earlier reviews/latest result when source validation is rejected.
- Map rejected CSV sources to safe import-specific UI copy and retain the file.
- Add two-user authorization, no-processing/no-mutation, source-boundary, and
  persisted-association tests; document the CSV contract and handoff.

## Validation

- Backend: **100 passed, 26 skipped**. PostgreSQL-specific tests were skipped
  because no disposable `TEST_POSTGRES_URL` was configured; hosted Supabase was
  not accessed.
- Frontend: **58 tests passed**; lint and production build passed.
- Ruff lint/format, compileall, application import, and diff whitespace checks passed.
- The UI change only corrects source-rejection copy; no layout or routes changed.
- Live hosted Supabase Auth and external providers were not exercised.

## Scope

This S1-019 branch is stacked on `S1-018-analysis-target-workspace` so the
workspace upload remains the only import UI. Keep this PR separate from PR #30;
after #30 merges, retarget this PR to `main`. CSV is the implemented
recovery/import mechanism. Primary URL/provider collection remains separate work;
no provider, migrations, dependencies, or fake fallback reviews are introduced.
Auth uses deterministic test doubles, not live Supabase.

Relates to #19

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

- Backend: **124 passed, zero skipped**, against SQLite and disposable local
  PostgreSQL 18.6 applying the committed migrations. The server was stopped afterward.
- Frontend: **35 tests passed**; lint and production build passed. Lint retains
  the existing set-state-in-effect warning in TargetWorkflowPage; no new warning.
- Ruff lint/format, compileall, application import, and diff whitespace checks passed.
- The UI change only corrects source-rejection copy; no layout or routes changed.
- Live hosted Supabase Auth and external providers were not exercised.

## Scope

This is an independent S1-019 branch. It does not include S1-018's workspace
redesign; see `docs/handoffs/s1-019-ingestion.md` when combining those branches.
CSV is the implemented recovery/import mechanism. Primary URL/provider collection
remains separate work; no provider, migrations, dependencies, or fake fallback
reviews are introduced. Auth uses deterministic test doubles, not live Supabase.

Closes #19

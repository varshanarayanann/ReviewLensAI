# S1-021 normalization handoff

## Assessment and provenance

Issue #21 is assigned to JasmineG8493, not Varsha. Draft PR #29 already contains
a tested pure normalizer, but the application did not call it before persistence,
and the Review table did not store its metadata. This handoff finishes those gaps
and confirms the raw mapping contract from S1-020. See
[the normalization contract](../review-normalization.md).

`varsha/s1-021-normalization-handoff` starts at her original `35d9ae1` branch and
merges S1-020's `003237a` branch. The shared reviews package conflict was resolved
by keeping her normalizer exports and the source adapter together. Her original
commits/authorship remain intact, and new contribution commits retain their actual
author. Main, the original remote branch, PR #29, and issue status are not changed.
No new PR is created for this handoff.

## Dependency and PR scope

**S1-020 / PR #39 is required for the integrated import pipeline.** It supplies
the CSV adapter and deterministic saved fixture. The pure normalizer itself does
not require it, but end-to-end ingestion does.

Keep PR #29 in draft until #39 is merged and the normalization branch is updated
from main. Before that, comparing #29 to main will also show its upstream S1-020
changes. Do not merge #29 into main to deliver #39 indirectly, and do not open a
second normalization PR. A review of only normalization changes is available via:

```powershell
git diff origin/varsha/s1-020-review-source-adapters...origin/varsha/s1-021-normalization-handoff
```

## Commands for the original author

Commit/stash unrelated local changes first. From the repository root:

```powershell
git fetch origin
git switch S1-021-review-normalization
git merge origin/varsha/s1-021-normalization-handoff
```

If the branch is not local yet, use
`git switch --track origin/S1-021-review-normalization` instead of the switch.
If she has added commits, merge normally and resolve conflicts; do not reset,
force-push, or discard local work.

After PR #39 merges:

```powershell
git fetch origin
git merge origin/main
# Resolve any integration conflicts and run the checks below.
git push origin S1-021-review-normalization
```

Pushing this original branch updates her existing draft PR #29, preserving her
as its PR author. Paste [the prepared PR description](s1-021-pr-description.md),
verify CI and the PR diff, and mark ready only after the dependency is merged and
only the intended normalization work remains. Keep actual commit attribution.

## Schema and verification

This handoff adds `backend/migrations/0003_add_review_source_metadata.sql`.
Apply it through the documented migration process before running the updated
application against a development database. No shared migration was auto-applied
and no earlier migration was modified. The integration fixture applies it in
disposable PostgreSQL databases automatically.

Backend checks (from `backend/`, virtual environment active):

```powershell
python -m ruff check .
python -m ruff format --check .
python -m compileall -q app tests
python -c "from app.main import create_app"
python -m pytest -ra
```

Frontend checks (from `frontend/`):

```powershell
npm run lint
npm run build
npm test
```

Set `TEST_POSTGRES_URL` only to a disposable PostgreSQL server with create/drop
database permission; otherwise those variants skip locally. CI supplies PostgreSQL
18. The migration test reconstructs the pre-0003 column shape only inside its
isolated test database to verify defaults for existing rows and JSONB constraints.
It never runs that setup against a shared Supabase project.

Validation results are recorded in the prepared PR description. Supabase Auth
remains mocked; live Google Maps/provider collection is not part of the tests.

Local handoff results: **150 backend tests passed with zero skipped**, including
PostgreSQL, and **35 frontend tests passed**. Lint/build/import/format checks passed
with only the pre-existing frontend lint warning; the temporary server is stopped.

## Integration reminders

- Preserve all-or-nothing HTTP import behavior while the normalizer reports valid
  candidates and individual rejections separately. Do not silently enable partial
  persistence or report a mixed batch as fully ingested.
- Keep metadata under `Review.source_metadata`; never unpack source fields into
  target ownership or ORM association arguments.
- When combining S1-019, keep one CSV adapter/preflight implementation, after parent
  authorization and before normalization. Update old parser spies to the adapter
  boundary rather than retaining duplicate inline parsing.
- S1-018 replaces the old import page; retain its workspace route and safe CSV
  error handling if merging that handoff too. S1-021 makes no additional UI change.
- Verify the next migration number before merging if another schema migration
  lands first. Add/renumber only an unapplied new migration; never edit an applied one.

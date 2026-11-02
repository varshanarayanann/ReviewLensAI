# S1-019 ingestion submission handoff

**Issue:** #19 — Submit Review Source for Ingestion

**Assigned author:** JasmineG8493

**Rules:** S1-BR-018, S1-BR-019, S1-BR-025

## Branch and authorship

The handoff branch is `varsha/s1-019-ingestion-handoff`, based directly on main
at `624bbf1`. It contains only S1-019 work and can be proposed independently of
the S1-018 workspace handoff. No existing teammate branch, main, issue status, or
PR was changed. No new PR was created. Contribution commits retain their actual
author; the teammate becomes the PR author when she opens it from her account.

No dedicated S1-019 branch/PR existed at inspection time. After reviewing the
code, she can create her own branch from the handoff:

```powershell
git fetch origin
git switch -c S1-019-submit-review-source origin/varsha/s1-019-ingestion-handoff
# Review changes and run the checks below.
git push -u origin S1-019-submit-review-source
```

Then open a new PR **from her account**, head `S1-019-submit-review-source`, base
`main`, using [the prepared PR description](s1-019-pr-description.md). Do not merge
into main as part of this handoff. If she already has a local S1-019 branch with
work, switch to that branch and merge the handoff instead of recreating/resetting
it. Resolve any conflicts and rerun checks before pushing. Keep issue #19's PR
separate from her S1-018 PR #30.

## Implementation and acceptance evidence

The supported implementation is the **existing CSV import path**, permitted by
the issue's practical-import alternative. This does not change the UI baseline's
preference for URL collection or claim a provider was selected/implemented.

- Authenticated requests reference an existing target through
  `POST /api/targets/{target_id}/ingestions`.
- Backend ownership checks run before CSV parsing; missing/cross-user targets
  return the same safe 404, with no parser call or stored changes.
- Strict request fields and CSV preflight reject absent, empty, malformed,
  oversized, or over-limit sources before creating an ingestion attempt.
- Structurally valid sources proceed through the existing recorded normalization
  and persistence flow. Valid submissions persist under the intended target.
- Source-validation failures preserve prior reviews and the previous latest run.
- The existing import UI maps 422 to CSV guidance rather than target-name/URL
  validation copy, hides raw response details, and retains the selected file.
- [The CSV contract](../csv-import-format.md) documents exact fields, limits,
  statuses, and the distinction between source rejection and a failed recorded run.

## Verification

Run backend commands inside `backend/`, with its virtual environment active:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m compileall -q app tests
python -c "from app.main import create_app"
python -m pytest -ra
```

Run frontend commands inside `frontend/`:

```powershell
npm run lint
npm run build
npm test
```

PostgreSQL variants require `TEST_POSTGRES_URL` pointing to a **disposable** server
with create/drop database permission. The fixture applies committed migrations
in isolated temporary databases; CI supplies PostgreSQL 18. Hosted Supabase Auth
and any external review provider remain mocked/not exercised.

The handoff's validation results are recorded in the prepared PR description.
Rerun checks after combining branches or resolving conflicts. No new application
dependencies, database migrations, or provider secrets are needed.

Local results: **124 backend tests passed with zero skipped**, including actual
PostgreSQL migrations, and **35 frontend tests passed**. Both builds/import checks
and all required lint/format checks passed; frontend lint retains its existing
TargetWorkflowPage set-state-in-effect warning. The disposable server was stopped.

## Combining with S1-018

The independent main-based handoff includes a small fix in the old
`TargetWorkflowPage.tsx` import UI. The S1-018 handoff replaces that import screen
with `AnalysisTargetWorkspacePage.tsx` and makes TargetWorkflowPage create-only.
When combining them, retain S1-018's create-only page and workspace route. Its
workspace upload handler already maps 422 to safe CSV guidance, so do not re-add
the removed `targetId` import branch or duplicate the old import form.

Keep S1-019's backend CSV preflight, strict request contract, byte/row limits, and
tests. In `TargetWorkflowPage.test.tsx`, keep S1-018's workspace-aware fixtures and
move the S1-019 rejected-source/file-retention assertion to the workspace tests
using `Reviews CSV file *`; S1-018 already covers upload 422 safe-error handling.
Use the shared CSV-source guidance where appropriate and rerun the full suites.

A merge-tree check against the published S1-018 handoff found a conflict in
`frontend/src/pages/TargetWorkflowPage.test.tsx`. The old page implementation
auto-merges but must still be reviewed: retain S1-018's create-only version,
without the old `targetId` conditional or unused message import. Do not interpret
an automatic merge as proof that TypeScript or combined UI tests will pass.
Combine these features when updating against main after the other PR merges, or
use a deliberately stacked PR; do not accidentally submit both issues as one PR.

S1-020 URL/provider extraction and S1-021 normalization integration are separate
work. This handoff does not choose a provider or change the current all-or-nothing
record policy into partial success. Reconcile those contracts explicitly when
integrating the normalization branch.

## Combining with S1-011 / PR #34

Both branches touch ingestion ownership setup, so a merge-tree check found a
small conflict in `backend/app/api/targets.py`. Retain the shared forbidden-extra
request configuration once, S1-011's explicit target creation fields, and this
ingestion order:

```python
target = owned(target_id, user, db)
records = read_csv_source(body.csv_text)
run = IngestionRun(target_id=target.id)
db.add(run)
```

Keep review `target_id=target.id` and iterate over the validated `records`.
Do not drop source preflight while resolving the conflict or move it before the
ownership check. S1-013 / PR #35 passed a merge-tree compatibility check directly.

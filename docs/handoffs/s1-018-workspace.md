# S1-018 workspace handoff

## Ownership and delivery

This handoff continues the existing `S1-018-analysis-target-workspace` foundation
at `478c84e`. The new branch is `varsha/s1-018-workspace-handoff`, with current
`main` (`624bbf1`) merged into that branch to integrate the already-merged target
and CSV APIs. Original commits and their authors are preserved; new contribution
commits retain their actual author. Neither `main` nor the teammate's remote
branch was changed, and no replacement PR was created.

The original author can update her existing [draft PR #30](https://github.com/varshanarayanann/ReviewLensAI/pull/30).
Pushing her original branch updates that PR and preserves her as the PR author.
There is no need to recreate the PR or change commit attribution.

## Integrate into the original branch

First commit or stash any unrelated local work. From the repository root:

```powershell
git fetch origin
git switch S1-018-analysis-target-workspace
git merge origin/varsha/s1-018-workspace-handoff
```

If the original branch has not changed, this is a fast-forward. If it has additional
commits, review/resolve the merge and rerun checks. Do not reset, force-push, or
discard local commits. If the branch is not local yet, replace the switch command
with `git switch --track origin/S1-018-analysis-target-workspace`.

Review the diff and run frontend lint/build/tests and the backend checks from the
README. PostgreSQL cases require `TEST_POSTGRES_URL` to a disposable server with
database creation/drop permission; CI supplies PostgreSQL 18 automatically.
Then push only the original feature branch:

```powershell
git push origin S1-018-analysis-target-workspace
```

Open PR #30, replace its outdated integration-unavailable description with
[the prepared PR description](s1-018-pr-description.md), verify the latest CI,
and mark it ready for review when satisfied. Do not merge it into main as part of
this handoff. Issue #18 closes only when the PR's closing reference is merged.

## What was completed

- Reuse `AnalysisTargetWorkspaceView` and its styling from the original branch.
- Keep exactly one `/targets/:targetId` route; use the existing create-target page
  only for `/targets/new`, then navigate to the created workspace.
- Load the authorized target and latest persisted ingestion result through the
  typed API client. Extend the protected target-read response with `platform`.
- Display target name, Google Maps platform, clickable saved source, and current
  status, including Not ingested when no run exists.
- Enable the existing CSV ingestion path, with validation, busy/duplicate-submit
  protection, safe errors, result display, and explicit refresh.
- Treat missing and inaccessible targets identically; expire rejected sessions;
  clear context across target/account changes and ignore stale responses/submissions.
- Preserve the original ownership checks and verify the response contract and
  cross-user denial on both SQLite and PostgreSQL.

## Validation of this handoff

- Frontend: **57 tests passed**, lint passed without warnings, production build passed.
- Backend: **80 tests passed, zero skipped**, including disposable PostgreSQL 18.6
  with the committed SQL migrations. The local server was stopped afterward.
- Ruff lint/format, compileall, application import, and diff whitespace checks passed.
- Browser fixture checks at **1280px, 768px, and 375px**: one H1, no horizontal
  overflow, CSV upload works, persisted result restores on refresh, and denied
  targets hide upload controls and raw error details. Screenshots were inspected.
- Supabase Auth was mocked; these are not live hosted Supabase/provider tests.
- Browser fixtures and tooling remain ignored local files, outside the delivery.

## Scope and integration notes

S1-018 supplies workspace context and an available ingestion path. The path uses
the real CSV API already on main. Primary collection from a saved Google Maps URL
still belongs to S1-020/provider integration; this handoff does not claim that it
exists. It adds no Summary/Ask tabs, provider SDK, AI functionality, or schema migration.

S1-017 [PR #36](https://github.com/varshanarayanann/ReviewLensAI/pull/36) supplies
Dashboard target cards. Its links already use `/targets/:targetId` and will open
this workspace when both features are merged. Without it, workspace navigation
still works through direct URLs and after creating a target. Do not copy its
whole implementation into PR #30.

When combining with S1-017, update its navigation test in
`frontend/src/pages/DashboardPage.test.tsx`: the workspace H1 now identifies the
target rather than using the previous generic `Import reviews` title. Replace:

```tsx
expect(await screen.findByRole('heading', { name: 'Import reviews' })).toBeInTheDocument()
```

with:

```tsx
expect(await screen.findByRole('heading', { name: target.name })).toBeInTheDocument()
```

Rerun the full frontend suite after this integration. Other unmerged feature
branches were not imported into this handoff. Shared responsive styles may need
deduplication when combining UI branches; retain token-based values and rerun the
three viewport checks after resolving any conflicts.

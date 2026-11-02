## Changes

Story rules: S1-BR-016 through S1-BR-018.

Completes S1-018 by connecting the workspace foundation to the authorized target
and persisted ingestion APIs. Selecting `/targets/:targetId` now opens actual
target context and a working CSV import path instead of an unavailable placeholder.

- Reuse the original workspace view and resolve the duplicate target route.
- Display the authorized target name, Google Maps platform, saved source link,
  and persisted ingestion status. Extend the target-read response with platform.
- Load/refresh the latest recorded result and enable CSV import with validation,
  duplicate-submit protection, busy states, and safe error handling.
- Keep missing/inaccessible targets indistinguishable and hide their ingestion
  controls. Clear stale target/account state and prevent uploads from an old page.
- Keep `/targets/new` dedicated to creation and open the workspace after success.

## Validation

- Frontend: **57 tests passed**; lint and production build passed.
- Backend: **80 tests passed, zero skipped**, against SQLite and disposable local
  PostgreSQL 18.6 applying the actual migrations. The server was stopped afterward.
- Ruff lint/format, compileall, application import, and whitespace checks passed.
- Browser checks at 1280/768/375px passed for layout, source wrapping, CSV upload,
  restored result, and denied-target presentation; screenshots inspected.
- Auth/provider fixtures are deterministic; live hosted Supabase was not exercised.

## Scope and integration

CSV import is the implemented ingestion path. URL-provider collection remains
S1-020 work; this PR does not claim that integration. No Sprint 2 features, new
application dependencies, or migrations are introduced.

Dashboard target cards are supplied separately by S1-017 PR #36 and already link
to this route. Direct navigation and post-creation navigation work independently.
When integrating #36, update its navigation test to expect the actual target-name
heading, as documented in `docs/handoffs/s1-018-workspace.md`.

## UI checklist

- [x] Reuses AppShell and the original workspace presentation component.
- [x] Uses CSS tokens, one H1, responsive source wrapping, and existing button styles.
- [x] Displays name, platform, source, and persisted basic ingestion state.
- [x] Implements loading, no-run, ready, failed, denied, and session-expired states.
- [x] Uses shared safe messages and labeled file validation; raw errors stay hidden.
- [x] Does not send owner IDs; backend verifies parent ownership.
- [x] Keyboard focus and desktop/tablet/mobile rendering checked.
- [x] Includes successful and failed import, auth, navigation, and stale-state tests.
- [x] Adds no fake runtime data, Summary/Ask tabs, or AI functionality.

Closes #18

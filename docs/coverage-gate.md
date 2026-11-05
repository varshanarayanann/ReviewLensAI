# Changed-code coverage gate (S2-001)

Every pull request must prove that the code it adds or changes is exercised by
automated tests. The gate measures only the lines in the pull request's diff, not
the whole project, so it blocks untested new behavior without rewarding a vanity
percentage.

Rules: S2-BR-027 through S2-BR-031.

## Mechanism

| Part | Coverage tool | Report |
| --- | --- | --- |
| Backend (`backend/app`) | [coverage.py](https://coverage.readthedocs.io/) through `pytest-cov` | `backend/coverage.xml` (Cobertura) |
| Frontend (`frontend/src`) | Vitest with `@vitest/coverage-v8` | `frontend/coverage/cobertura-coverage.xml` |

[diff-cover](https://github.com/Bachmann1234/diff_cover) compares each report
with `git diff origin/<base branch>...HEAD` and reports the percentage of changed,
executable lines that the tests ran.

In `.github/workflows/ci.yml`, the `Backend` and `Frontend` jobs run their tests with
coverage and then run a **Changed-code coverage gate** step on pull requests. The
step prints the uncovered lines in the job log and writes the same report to the
job's summary page, so reviewers can see it before merging.

## Policy

- **Threshold:** at least **80% of changed executable lines** must be covered, checked
  separately for the backend and the frontend. The value is
  `CHANGED_CODE_COVERAGE_THRESHOLD` at the top of `ci.yml`.
- A pull request that changes no backend (or no frontend) code passes that part
  of the gate: there are no changed lines to measure.
- The gate runs on pull requests. Pushes to `main` still record overall coverage
  in the job log.
- Because the gate is a step inside the required `Backend` and `Frontend` checks,
  a failing gate fails the check, and branch protection on `main` blocks the merge
  (see [Merge protection](../README.md#merge-protection)).
- 80% leaves room for lines that are impractical to reach in a unit test (for
  example a defensive log statement), while a new feature, branch, or endpoint
  without tests falls well below it.

### AI and Q&A code

- Q&A orchestration, review-context building, and scope-guard code are **not**
  excluded. Their changed lines must reach the same threshold (S2-BR-027).
- Coverage in CI must come from deterministic tests that mock or stub the LLM
  boundary. CI has no model API key, and tests must not depend on an exact
  sentence from a live model (S2-BR-029).
- A live-model test or evaluation script may supplement the suite, but it must not
  run in CI and does not count toward the gate (S2-BR-031).

## Exclusions

| Excluded | Why |
| --- | --- |
| Test files (`backend/tests/`, `frontend/src/**/*.test.ts(x)`, `frontend/src/test/`) | They are the verification, not the behavior being verified. |
| `frontend/src/main.tsx` | Bootstrap that mounts `<App />` into the page; `App` itself is tested. |
| `frontend/src/**/*.d.ts` | Type declarations contain no executable code. |
| `backend/migrations/*.sql` | SQL, not Python; the PostgreSQL migration tests in CI verify them. |
| `if TYPE_CHECKING:` blocks (backend) | Imports that only run during type checking, never at runtime. |
| `backend/evals/` | Evaluation tooling run manually against a live model, not application code. `tests/test_scope_guard_eval.py` still tests it. |
| Config, CSS, docs, and workflow files | Not executable application code; coverage tools do not instrument them. |

Configuration lives in `[tool.coverage.*]` in `backend/pyproject.toml` and in the
`coverage` section of `frontend/vitest.config.ts`.

Any other exclusion needs a reason a reviewer can check. `# pragma: no cover`
(Python) or `/* v8 ignore next */` (TypeScript) must be followed by a short
comment explaining why the line cannot reasonably be tested, and the reviewer
should challenge it if a test is practical.

## Running the check locally

Run `git fetch origin` first so the comparison uses the current `main`. Locally,
diff-cover includes committed, staged, and unstaged changes, but **not new files
you have not yet added**: run `git add` on new files before checking.

**Backend** (from `backend/`, with the virtual environment active):

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest --cov --cov-report=xml --cov-report=term
diff-cover coverage.xml --compare-branch=origin/main --fail-under=80
```

Tests marked PostgreSQL-only are skipped unless `TEST_POSTGRES_URL` points to a
disposable database, so local coverage can be slightly lower than in CI. The CI
result is authoritative.

**Frontend** (from `frontend/`; diff-cover comes from the backend's virtual
environment):

```powershell
npm install
npm run test:coverage
..\backend\.venv\Scripts\diff-cover.exe coverage\cobertura-coverage.xml --compare-branch=origin/main --fail-under=80
```

On macOS/Linux, use `../backend/.venv/bin/diff-cover coverage/cobertura-coverage.xml ...`.

The output lists each changed file with its coverage and the line numbers that
no test ran. Add tests that exercise those lines (observable behavior, not
implementation details), then run the commands again.

## Demonstrating that the gate fails

Add a function with a branch to any file in `backend/app` (or `frontend/src`)
without a test, then run the local commands above:

```text
Failure. Coverage is below 80%.
backend/app/reviews/normalization.py (25.0%): Missing lines 124-126
```

Add a test that calls both branches and run them again: the file reports 100% and
the command exits successfully. In a pull request, the same untested change makes
the `Backend` or `Frontend` check fail at the **Changed-code coverage gate** step.

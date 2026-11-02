# S1-020 — Review ingestion approach

**Rules:** S1-BR-019 through S1-BR-021, S1-BR-024.

## Selected implementation

This change completes the issue's **supplied export / practical import** option:
users upload a CSV containing reviews for their saved Google Maps analysis target.
FastAPI obtains individual records from the submitted text through a dedicated
CSV adapter. No provider account, scraping SDK, or browser-side data service is
required for this implemented path.

Google Maps remains the supported platform. CSV remains the recovery/import
mechanism in the team's UI baseline. **Live collection from the saved Google Maps
URL is not implemented by this PR** and remains a separately selected/configured
provider integration. This document does not claim that an outside API suggestion
was a team decision. S1-020's import alternative is usable now without that setup.

## Data flow and boundaries

```text
User-supplied Google Maps review CSV
  → protected POST /api/targets/{target_id}/ingestions
  → existing target + verified ownership check
  → app.reviews.csv_source.parse_csv_reviews
  → raw record mappings (review_text, rating, optional metadata)
  → existing review-value validation and explicit persistence transaction
  → recorded ingestion result
```

The adapter depends only on Python's `csv` and `io` modules. It has no FastAPI,
database, UI, filesystem-fixture, network, or provider dependencies and can be
tested directly. A CSV record is identified by its mapping/list position, not a
physical line: quoted newlines can occur inside a single review. Optional source
review IDs remain unchanged when supplied. New database UUIDs identify persisted
reviews; source IDs do not grant access or establish ownership.

The raw mapping interface is compatible with the unmerged S1-021 normalizer's
`review_text` / `rating` inputs and top-level optional metadata. This PR leaves
normalization policy at the next boundary. The adapter neither repairs
invalid ratings nor invents missing review text. Optional metadata is retained by
the adapter; S1-021's integrated normalizer stores it in `Review.source_metadata`
alongside canonical text/rating. See [the normalization contract](review-normalization.md).

## Source contract

See [CSV import format](csv-import-format.md) for exact fields and boundaries.
The source comes exclusively from the authenticated request's `csv_text`. The
saved business URL provides target context and is not fetched by this adapter.
Selecting the correct target associates the supplied business export with that
target; ReviewLens does not independently verify export provenance.

Missing/invalid source structure returns a safe 422 before an attempt is recorded.
Source failures never select a bundled fixture, generate reviews, or silently
switch data sources. Review-value or persistence failures after source acceptance
retain the existing recorded-failure semantics and preserve prior reviews.
The frontend maps source rejection to import guidance and preserves the file.

## Test evidence and fixture provenance

`backend/tests/fixtures/google_maps_export.csv` is an explicitly synthetic saved
representative export for deterministic tests, not a live scrape or production
seed. It covers individual text/rating records, multiline/comma/quote handling,
Unicode, source IDs, dates, and missing optional metadata. Application code never
loads the fixture directory. No real provider/live website is needed by ordinary
tests, and no live collection is claimed as verification.

Unit tests call the adapter directly. Integration tests submit the saved fixture
through the protected API and compare the exact persisted text/rating and target
association. They also verify authorization before adapter invocation, safe
source errors, no fallback insertion, and preservation of previous reviews/results.
SQLite and disposable PostgreSQL tests apply the repository's normal fixtures and
actual SQL migrations. See the PR for the final run results.

## Combining pending branches

- **S1-019 handoff:** replace the inline CSV parsing/preflight implementation with
  this adapter, retaining validation after ownership and before recording work.
  Keep its strict request fields, persisted-target associations, and submission
  tests. Do not keep two independent parsers or silently change error timing.
- **S1-013 / S1-019 tests:** spies on `app.api.targets.csv.DictReader` need to target
  `app.api.targets.parse_csv_reviews` after this refactor. Denied requests must
  still fail without invoking the adapter.
- **S1-021:** keep its normalization module/exports when resolving the shared
  `app/reviews/__init__.py` addition. Feed the adapter's raw mappings directly to
  its normalizer. The S1-021 handoff connects it while preserving the current
  all-or-nothing API result contract; no partial persistence is claimed.
- **S1-018:** retain its create-only TargetWorkflowPage and workspace upload
  handler. The old import-page error-copy regression belongs in workspace tests
  after that screen replacement; the source API and adapter remain the same.

No main-branch merge, repository setting change, provider purchase, or live
credential operation is part of this implementation.

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
normalization policy in the existing ingestion flow. The adapter neither repairs
invalid ratings nor invents missing review text. Optional metadata is retained by
the adapter; the current persistence model saves text and rating only.

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

## Integration with the current workflow

S1-019 submission and S1-018 workspace behavior are retained. The source adapter
replaces the inline preflight, after target authorization and before recording an
attempt. Request fields, persisted-target associations, and submission tests remain
strict. Authorization spies target `app.api.targets.parse_csv_reviews` and prove
denied requests never invoke it. Workspace tests verify safe CSV guidance and
retention of the selected file after rejection.

S1-021 remains a separate PR. Keep its normalization module/exports when resolving
the shared `app/reviews/__init__.py` addition, and feed the adapter's raw mappings
to its normalizer. Reconcile partial-record rejection with the current all-or-nothing
API result contract before connecting it; no partial success is claimed here.

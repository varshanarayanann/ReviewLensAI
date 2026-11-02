# S1-021 — Canonical review normalization

**Issue owner:** JasmineG8493. **Rules:** S1-BR-020, S1-BR-021, S1-BR-024.

## Contract and integration

The S1-020 CSV adapter returns raw mappings with `review_text`, `rating`, and
optional source fields. `normalize_reviews` is called by the ingestion handler
before constructing any ORM Review objects. It remains independently testable
without the UI, database, or source adapter.

| Canonical field | Chosen behavior |
| --- | --- |
| `review_text` | Required string, trimmed at its boundaries; nonblank; NUL is rejected because PostgreSQL text cannot store it. Internal newlines/Unicode remain unchanged. |
| `rating` | Required whole-number value 1–5, returned as Python int. Integral numbers/numeric strings such as `4`, `4.0`, and `4e0` are accepted. Booleans, fractions, non-finite values, and other types are rejected. |
| `source_metadata` | All other source fields, deep-copied into an object; empty object when absent. Fields such as source ID, display name, date, URL, and unknown metadata are preserved without inferring missing values or parsing dates. |

Metadata must be JSON-safe: string keys, strings without NUL, null, booleans,
integers, finite floats, arrays, and objects. Unsupported/cyclic values are
reported as an invalid-record reason rather than silently converted or dropped.
This keeps canonical values compatible with PostgreSQL JSONB. Optional empty
CSV cells remain empty strings/null as supplied; no placeholder identity is added.

Source fields named `owner_id`, `target_id`, or `run_id` remain untrusted metadata.
The API explicitly assigns actual associations from the authorized target/run;
metadata never controls ownership, routing, or database identifiers.

## Invalid-record policy

The normalizer returns valid canonical candidates and indexed rejection reasons
separately, preserving the original input and otherwise usable candidates. It
does not mutate records or silently pretend an invalid record was normalized.

The **HTTP import remains all-or-nothing**, matching the existing CSV contract:
if any record is rejected, the attempt is recorded as failed and no reviews from
that batch are persisted. Earlier reviews remain intact. Valid candidates in the
normalization result remain usable to callers, but the API does not claim partial
success. Counts reflect actual committed rows. Supporting partial persistence
would require an explicit result/status contract change and is outside this handoff.

Malformed CSV structure still returns 422 before an attempt is created, as in
S1-020. Invalid individual values after source acceptance produce a recorded
failed run. This distinction is intentional and covered by tests.

## Persistence and migration

`Review.source_metadata` stores the canonical metadata object. SQLAlchemy uses
JSONB on PostgreSQL and JSON for SQLite test coverage. New ordered migration
`0003_add_review_source_metadata.sql` adds a non-null JSONB column with `{}` as
the default for existing/new rows and an object-type check. No applied migration
is edited. Follow the migration README when deploying to a development/shared
database; no shared database was changed during the handoff.

Tests verify exact adapter → normalizer → database text/rating/metadata, empty
metadata defaults, forged association fields remaining inert, mixed-batch atomic
failure, and the actual PostgreSQL migration against an existing review row.
SQLite verifies ORM round-trip behavior; it does not establish JSONB equivalence.

## Existing draft and dependency

The original pure normalizer and its tests came from `S1-021-review-normalization`
at `35d9ae1` / draft PR #29. They already cover the issue's basic valid/missing/
invalid/optional cases. The remaining gaps were live ingestion integration,
confirmation of the S1-020 raw-record contract, metadata persistence, and a stated
batch-failure policy.

This handoff integrates S1-020 branch `003237a` / PR #39 into a descendant of the
original normalization branch. PR #39 is an upstream dependency, not already on
main. Follow [the handoff instructions](handoffs/s1-021-normalization.md) to update
PR #29 after #39 merges, retaining the original author's commits and PR ownership.

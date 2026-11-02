# CSV review import format

S1-020 imports user-supplied Google Maps business-review exports through the
existing recovery path. It does not collect data from the saved URL.

## Request and records

Use the existing authenticated `POST /api/targets/{target_id}/ingestions` endpoint
with a JSON string field, not multipart data:

```json
{"csv_text":"rating,review_text\n5,Text from the submitted export"}
```

- Required column names: exactly `rating` and `review_text`, in either order.
- Provide a header and 1–1,000 CSV records. Quoted commas, quotes, and embedded
  newlines are supported. Blank lines are ignored; a leading UTF-8 BOM is accepted.
- Duplicate/blank column names, extra unnamed row values, malformed CSV, or an
  empty/header-only source are rejected rather than silently repaired or truncated.
- Maximum UTF-8 source size: 1,000,000 bytes; the request string also has a
  1,000,000-character limit. The standard Python CSV reader's per-field size limit
  also applies. Files/fields exceeding parser limits get the same safe source error.
- Raw text and rating strings are preserved for normalization. The current
  ingestion flow requires nonblank trimmed text and whole-number ratings 1–5.
- Other named columns, such as `source_review_id`, `reviewer_name`, `review_date`,
  and `review_url`, are retained in adapter output, including empty optional cells.
  S1-021 stores these fields in the canonical Review's JSON-safe `source_metadata`
  object; it does not use them as trusted ownership or association fields.

Only `csv_text` is accepted in the request body; ownership and associations come
from verified identity and the authorized target path. No API key is required.

## Outcomes

Parent authorization happens before source parsing. Missing/invalid authentication
returns 401; missing and inaccessible targets share the same 404. Invalid source
structure returns 422 before creating a run, leaving the prior latest result and
reviews intact. The UI shows safe CSV-specific guidance and retains the selection.

Accepted source records proceed to existing normalization/persistence. A malformed
review value fails the entire recorded import; previously valid reviews remain.
The 200 result reports actual `state`, `persisted_count`, `run_id`, `target_id`,
and safe `message`. There is no automatic fallback to test fixtures or sample data.

On the S1-021 integration branch, `normalize_reviews` produces canonical candidates
and indexed rejections before ORM objects are built. Any rejection fails the
recorded batch atomically; valid candidates are not silently reported as persisted.
See [normalization policy](review-normalization.md) for rating and metadata rules.

See [the ingestion approach](review-ingestion-approach.md) for adapter boundaries,
fixture provenance, tests, and pending branch integration notes.

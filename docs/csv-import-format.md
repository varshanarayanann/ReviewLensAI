# CSV review source contract

S1-019 uses the CSV recovery mechanism already implemented on main. It is a
practical import path for Google Maps review data, not automatic collection from
the saved target URL. Primary URL/provider integration remains separate work.

## Request

Send an authenticated `POST /api/targets/{target_id}/ingestions` request with JSON:

```json
{"csv_text":"rating,review_text\n5,Helpful staff"}
```

The target must already exist and belong to the verified caller. The backend
uses the UUID path parameter and authenticated identity; it accepts no owner,
user, target, run, provider, or source-URL override fields in the body. The browser
uploads a `.csv` file by reading its text and sending this JSON, not multipart data.

## Source requirements

- Provide a nonempty string containing a CSV header and **1–1,000 data records**.
- Required column names are exactly **`rating`** and **`review_text`**. Header
  order may vary; duplicate column names and rows with extra unnamed values are
  rejected. Other named columns are accepted but their metadata is not currently
  persisted by this importer.
- Maximum source size is **1,000,000 UTF-8 bytes**, including any BOM. The JSON
  string also has a 1,000,000-character request limit. JSON overhead is not part
  of the source-byte limit. Normal CSV quoting/parser validity rules apply.
- A leading UTF-8 BOM is accepted. Whitespace-only content, BOM-only content,
  header-only files, missing required headers, malformed quoting, and excessive
  row/byte counts are rejected before an attempt is recorded.
- Within a structurally accepted source, each review needs nonblank text and an
  integer rating 1–5. Existing normalization trims surrounding review-text
  whitespace. Invalid review values reject the entire recorded ingestion; partial
  ingestion is not implemented. Previously persisted reviews remain intact.

The saved Google Maps URL identifies the target's source context. This CSV path
does not fetch it or require provider credentials. Supplying `source_url` instead
of `csv_text` does not initiate URL ingestion.

## Authorization, validation, and results

Authentication and the request schema are validated by FastAPI. The handler checks
the target's existence and verified ownership **before calling the CSV parser**.
Only an owned target with an accepted CSV source gets an `IngestionRun`; the
existing normalization/persistence flow then records the real outcome.

| Result | Behavior |
| --- | --- |
| Missing/invalid authentication | 401; no source processing or new records |
| Authentication infrastructure unavailable | 503; no source processing |
| Missing or another user's target | Same safe 404 response; no CSV parsing or mutations |
| Missing/wrong request fields or unusable source | 422; no new attempt/reviews and latest recorded result unchanged |
| Accepted source | 200 with recorded `run_id`, `target_id`, `state`, `persisted_count`, and safe `message` |

After acceptance, a normalization/persistence failure returns a recorded `failed`
outcome with zero new reviews. HTTP 200 does not itself imply ingestion succeeded.
`GET /api/targets/{target_id}/ingestions/latest` restores the latest recorded result.
Client errors must use safe import guidance, never raw parser/database messages.

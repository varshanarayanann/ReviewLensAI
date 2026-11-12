# Google Maps collection

ReviewLens collects Google-native reviews from the active target's saved Maps
URL using Apify's maintained `compass/google-maps-reviews-scraper` actor.
The authenticated backend performs collection and persistence. The browser
submits an empty JSON object to
`POST /api/targets/{target_id}/ingestions/google-maps`.
CSV import remains available at the existing ingestion endpoint.

## Local setup

Create an Apify account and copy an API token from the console's API settings.
Add these settings to the ignored `backend/.env` file, then restart the backend:

```dotenv
APIFY_API_TOKEN=your-apify-token
REVIEW_MAX_PER_RUN=20
REVIEW_MAX_CHARGE_USD=0.10
```

Keep the token server-side. Leave the frontend environment unchanged.
Without a token, the collection endpoint returns a safe 503 before creating
an attempt. Set up the actor in your Apify account if the provider requires
accepting its terms or activating access. Provider credits and access are
managed in Apify.

## Collection and results

1. Open an owned target with a Google Maps place URL.
2. Click **Ingest reviews**. The backend verifies ownership before collection.
3. The provider receives the saved URL, newest-first sorting, Google-only origin,
   and the configured review count. Reviewer personal-data collection is disabled.
4. A persisted run records processing, success, partial success, or failure.
   Valid text/rating records use the existing normalizer and persistence path.
   Invalid records are rejected and counted. Failed collection retains saved reviews.
5. Successful collection refreshes the persisted summary and enables Q&A when
   written reviews are available.

Collection runs synchronously. The actor has a 120-second runtime limit, and
the HTTP call has a 135-second timeout. The response is limited to 4 MB.
Responses exceeding the configured review count are rejected. A provider
timeout, malformed response, or collection failure records a failed run.
An empty response also records failure with zero saved reviews.

The default limit is 20 reviews, configurable from 1 to 1,000. The default
provider spending cap is USD 0.10 per attempt, configurable up to USD 5.
The actor may return fewer reviews. Star-only reviews are rejected because
ReviewLens requires written review text. Repeated imports append records,
matching CSV behavior. Re-importing the same place can produce duplicates.
Avoid repeated collection against the shared demo targets.

Optional source IDs and dates reach normalization, while the current Review
table stores text and rating. Source metadata persistence and deduplication
remain separate work. Review availability and source access depend on the
provider. Follow the applicable data-use terms for the dataset.

## Verification

Ordinary tests use mocked HTTP responses and injected sources. They verify
the fixed provider host, bearer-token handling, request limits, response parsing,
owned-target checks, partial records, failed attempts, and preservation of saved
reviews. They never call a paid provider. Run the backend and frontend checks
documented in README, including changed-code coverage.

Provider references:

- [Actor and output contract](https://apify.com/compass/google-maps-reviews-scraper)
- [Published input definition](https://api.apify.com/v2/acts/compass~google-maps-reviews-scraper/builds/default)
- [Synchronous run API](https://docs.apify.com/api/v2/actor-run-sync-get-dataset-items-post)

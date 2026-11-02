# Review-source fixtures

`google_maps_export.csv` is an explicitly synthetic, representative supplied-export
fixture. It contains no captured personal reviews and is used only by tests.
Its fixed rows cover written text, ratings, quoted commas/newlines/quotes, Unicode,
source IDs, and optional metadata. Test IDs are not live Google review identifiers.

Application code never reads this directory. Production ingestion must parse the
user's submitted source; failures must not select this fixture or generate reviews.

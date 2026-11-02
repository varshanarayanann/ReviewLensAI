"""Read supplied Google Maps review exports without UI or database dependencies.

Records retain source field names and raw values for the normalization boundary.
No provider request, inferred review, fixture, or replacement data is used here.
"""

import csv
import io

MAX_SOURCE_BYTES = 1_000_000
MAX_SOURCE_RECORDS = 1000


class ReviewSourceError(ValueError):
    """The submitted source cannot be read as a supported review export."""


def parse_csv_reviews(
    source: str,
    *,
    max_records: int = MAX_SOURCE_RECORDS,
    max_bytes: int = MAX_SOURCE_BYTES,
) -> list[dict[str, str | None]]:
    """Return one mapping per CSV record, including optional source metadata.

    Quoted commas/newlines are interpreted by csv.DictReader, not line splitting.
    Individual text/rating values are left for review normalization to validate.
    Limits are positive, bounded caller controls; excess input is rejected rather
    than silently truncated. Blank lines are ignored by the standard CSV reader.
    """
    if not 1 <= max_records <= MAX_SOURCE_RECORDS:
        raise ValueError("Invalid source record limit")
    if not 1 <= max_bytes <= MAX_SOURCE_BYTES:
        raise ValueError("Invalid source byte limit")
    try:
        if not isinstance(source, str) or len(source.encode("utf-8")) > max_bytes:
            raise ReviewSourceError("Invalid CSV source")
        reader = csv.DictReader(
            io.StringIO(source.lstrip("\ufeff"), newline=""), strict=True
        )
        headers = reader.fieldnames or []
        if (
            not {"rating", "review_text"}.issubset(headers)
            or len(set(headers)) != len(headers)
            or any(not header.strip() for header in headers)
        ):
            raise ReviewSourceError("Invalid CSV source")
        records = []
        for record in reader:
            if None in record or len(records) >= max_records:
                raise ReviewSourceError("Invalid CSV source")
            records.append(record)
        if not records:
            raise ReviewSourceError("Invalid CSV source")
        return records
    except (csv.Error, UnicodeError):
        # Parser messages can contain submitted values. Keep diagnostics bounded.
        raise ReviewSourceError("Invalid CSV source") from None

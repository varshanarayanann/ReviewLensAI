"""Normalize Google Maps and CSV review records for the application.

Ratings must be whole-star values from 1 through 5, accepting numeric strings
for CSV-style inputs. Google Maps ingestion enables rating-only records;
CSV callers require nonblank written text. Other fields are retained unchanged
in source_metadata for downstream use.
"""

from collections.abc import Iterable, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import StrEnum


class ReviewRejectionReason(StrEnum):
    INVALID_RECORD = "record_not_mapping"
    MISSING_REVIEW_TEXT = "missing_review_text"
    BLANK_REVIEW_TEXT = "blank_review_text"
    INVALID_REVIEW_TEXT = "invalid_review_text"
    MISSING_RATING = "missing_rating"
    INVALID_RATING = "invalid_rating"


@dataclass(frozen=True)
class NormalizedReview:
    review_text: str
    rating: int
    source_metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RejectedReview:
    index: int
    reason: ReviewRejectionReason


@dataclass(frozen=True)
class ReviewNormalizationResult:
    reviews: tuple[NormalizedReview, ...]
    rejected: tuple[RejectedReview, ...]


def normalize_reviews(
    records: Iterable[object], *, allow_rating_only: bool = False
) -> ReviewNormalizationResult:
    """Normalize records independently, optionally allowing rating-only data.

    Google Maps collection opts in. CSV callers keep requiring written text.
    Empty text is preserved as an empty string, never a fabricated comment.
    """
    normalized: list[NormalizedReview] = []
    rejected: list[RejectedReview] = []

    for index, record in enumerate(records):
        review, reason = _normalize_record(record, allow_rating_only=allow_rating_only)
        if review is None:
            rejected.append(RejectedReview(index=index, reason=reason))
        else:
            normalized.append(review)

    return ReviewNormalizationResult(
        reviews=tuple(normalized),
        rejected=tuple(rejected),
    )


def _normalize_record(
    record: object, *, allow_rating_only: bool = False
) -> tuple[NormalizedReview | None, ReviewRejectionReason | None]:
    if not isinstance(record, Mapping):
        return None, ReviewRejectionReason.INVALID_RECORD

    if "review_text" not in record and not allow_rating_only:
        return None, ReviewRejectionReason.MISSING_REVIEW_TEXT

    raw_text = record.get("review_text")
    if raw_text is None and allow_rating_only:
        raw_text = ""
    if not isinstance(raw_text, str):
        return None, ReviewRejectionReason.INVALID_REVIEW_TEXT
    review_text = raw_text.strip()
    if not review_text and not allow_rating_only:
        return None, ReviewRejectionReason.BLANK_REVIEW_TEXT

    if "rating" not in record:
        return None, ReviewRejectionReason.MISSING_RATING

    rating = _normalize_rating(record["rating"])
    if rating is None:
        return None, ReviewRejectionReason.INVALID_RATING

    metadata = deepcopy(
        {
            key: value
            for key, value in record.items()
            if key not in {"review_text", "rating"}
        }
    )
    return (
        NormalizedReview(
            review_text=review_text,
            rating=rating,
            source_metadata=metadata,
        ),
        None,
    )


def _normalize_rating(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        return None

    try:
        rating = Decimal(str(value).strip())
    except InvalidOperation:
        return None

    if (
        not rating.is_finite()
        or rating != rating.to_integral_value()
        or not Decimal(1) <= rating <= Decimal(5)
    ):
        return None
    return int(rating)

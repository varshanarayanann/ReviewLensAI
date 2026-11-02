from copy import deepcopy
from decimal import Decimal

import pytest

from app.reviews.normalization import (
    NormalizedReview,
    ReviewRejectionReason,
    normalize_reviews,
)


def test_normalizes_valid_review_and_preserves_optional_metadata() -> None:
    raw_review = {
        "review_text": "  Excellent service.  ",
        "rating": "5",
        "source_review_id": "review-123",
        "reviewer_name": "A Reviewer",
        "review_date": "2026-10-31",
        "review_url": "https://maps.example/reviews/review-123",
        "language": "en",
    }

    result = normalize_reviews([raw_review])

    assert result.reviews == (
        NormalizedReview(
            review_text="Excellent service.",
            rating=5,
            source_metadata={
                "source_review_id": "review-123",
                "reviewer_name": "A Reviewer",
                "review_date": "2026-10-31",
                "review_url": "https://maps.example/reviews/review-123",
                "language": "en",
            },
        ),
    )
    assert result.rejected == ()


def test_rejects_missing_review_text() -> None:
    result = normalize_reviews([{"rating": 4}])

    assert result.reviews == ()
    assert result.rejected[0].reason is ReviewRejectionReason.MISSING_REVIEW_TEXT


def test_rejects_non_string_review_text() -> None:
    result = normalize_reviews([{"review_text": 123, "rating": 4}])

    assert result.reviews == ()
    assert result.rejected[0].reason is ReviewRejectionReason.INVALID_REVIEW_TEXT


def test_rejects_blank_review_text() -> None:
    result = normalize_reviews([{"review_text": " \t ", "rating": 4}])

    assert result.reviews == ()
    assert result.rejected[0].reason is ReviewRejectionReason.BLANK_REVIEW_TEXT


def test_rejects_missing_rating() -> None:
    result = normalize_reviews([{"review_text": "Good"}])

    assert result.reviews == ()
    assert result.rejected[0].reason is ReviewRejectionReason.MISSING_RATING


def test_rejects_invalid_ratings() -> None:
    for value in (0, 6, "not a rating", 4.5, True):
        result = normalize_reviews([{"review_text": "Good", "rating": value}])

        assert result.reviews == ()
        assert result.rejected[0].reason is ReviewRejectionReason.INVALID_RATING


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf"), Decimal("NaN"), Decimal("Infinity")],
)
def test_rejects_non_finite_ratings(value: float | Decimal) -> None:
    result = normalize_reviews([{"review_text": "Good", "rating": value}])

    assert result.reviews == ()
    assert result.rejected[0].reason is ReviewRejectionReason.INVALID_RATING


@pytest.mark.parametrize("record", [None, [], "not a review"])
def test_rejects_non_mapping_records(record: object) -> None:
    result = normalize_reviews([record])

    assert result.reviews == ()
    assert result.rejected[0].index == 0
    assert result.rejected[0].reason is ReviewRejectionReason.INVALID_RECORD


@pytest.mark.parametrize("value", [True, False])
def test_rejects_boolean_ratings(value: bool) -> None:
    result = normalize_reviews([{"review_text": "Good", "rating": value}])

    assert result.reviews == ()
    assert result.rejected[0].reason is ReviewRejectionReason.INVALID_RATING


def test_absent_optional_metadata_is_an_empty_mapping() -> None:
    result = normalize_reviews([{"review_text": "Good", "rating": 4}])

    assert result.reviews[0].source_metadata == {}


def test_preserves_optional_metadata_without_mutating_input() -> None:
    raw_review = {
        "review_text": "Good",
        "rating": 4,
        "reviewer_name": "A Reviewer",
        "source_metadata": {"language": "en", "provider_flags": ["verified"]},
    }
    original = deepcopy(raw_review)

    result = normalize_reviews([raw_review])

    assert raw_review == original
    assert result.reviews[0].source_metadata == {
        "reviewer_name": "A Reviewer",
        "source_metadata": {"language": "en", "provider_flags": ["verified"]},
    }
    result.reviews[0].source_metadata["source_metadata"]["language"] = "fr"
    assert raw_review["source_metadata"]["language"] == "en"


def test_mixed_batch_keeps_valid_reviews_and_reports_rejections() -> None:
    result = normalize_reviews(
        [
            {"review_text": "First", "rating": 5, "reviewer_name": "Reviewer"},
            {"review_text": "  ", "rating": 4},
            {"review_text": "Third", "rating": 2},
            None,
            {"review_text": "Missing rating"},
        ]
    )

    assert [review.review_text for review in result.reviews] == ["First", "Third"]
    assert [review.rating for review in result.reviews] == [5, 2]
    assert [rejection.index for rejection in result.rejected] == [1, 3, 4]
    assert [rejection.reason for rejection in result.rejected] == [
        ReviewRejectionReason.BLANK_REVIEW_TEXT,
        ReviewRejectionReason.INVALID_RECORD,
        ReviewRejectionReason.MISSING_RATING,
    ]

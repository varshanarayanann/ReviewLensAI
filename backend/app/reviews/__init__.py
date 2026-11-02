"""Source adapters and normalization for ReviewLens review ingestion."""

from app.reviews.normalization import (
    NormalizedReview,
    RejectedReview,
    ReviewNormalizationResult,
    ReviewRejectionReason,
    normalize_reviews,
)

__all__ = [
    "NormalizedReview",
    "RejectedReview",
    "ReviewNormalizationResult",
    "ReviewRejectionReason",
    "normalize_reviews",
]

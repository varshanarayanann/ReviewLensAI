"""Bounded complete-dataset context, rebuilt from owned persisted rows per call."""

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisTarget
from app.models.ingestion import Review
from app.qa.llm import ReviewContext

MAX_CONTEXT_REVIEWS = 1000
MAX_CONTEXT_BYTES = 64_000


class ContextTooLargeError(Exception):
    """The complete dataset exceeds the application context budget."""


def review_context(
    db: Session, owner_id: UUID, target_id: UUID
) -> tuple[ReviewContext, ...]:
    """Return all authorized reviews or fail; never silently sample/truncate.

    Project columns rather than ORM entities to avoid identity-map cached text.
    The byte budget measures compact UTF-8 JSON records including IDs and rating;
    it is not a provider token count. Adapters must also check their token window.
    """
    statement = (
        select(Review.id, Review.target_id, Review.rating, Review.review_text)
        .join(AnalysisTarget, Review.target_id == AnalysisTarget.id)
        .where(Review.target_id == target_id, AnalysisTarget.owner_id == owner_id)
        .order_by(Review.id)
        .limit(MAX_CONTEXT_REVIEWS + 1)
        .execution_options(yield_per=25)
    )
    context: list[ReviewContext] = []
    size = 2  # JSON array brackets.
    with db.execute(statement) as rows:
        for row in rows:
            record = {
                "review_id": str(row.id),
                "target_id": str(row.target_id),
                "rating": row.rating,
                "text": row.review_text,
            }
            size += len(
                json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode(
                    "utf-8"
                )
            ) + bool(context)
            if len(context) == MAX_CONTEXT_REVIEWS or size > MAX_CONTEXT_BYTES:
                raise ContextTooLargeError
            context.append(
                ReviewContext(row.id, row.target_id, row.rating, row.review_text)
            )
    return tuple(context)

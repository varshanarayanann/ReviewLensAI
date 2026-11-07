"""Acceptance coverage for S2-010, S2-012, S2-016 and S2-019."""

import json

import pytest

from app.qa import context
from tests.test_review_dataset_integration import as_user as as_user
from tests.test_review_dataset_integration import ask, create_target, ingest
from tests.test_target_workflow import database as database


@pytest.fixture
def dataset(client, as_user):
    owner = as_user()
    target = create_target(client, owner, "Cafe")
    ingest(client, owner, target, 'rating,review_text\n5,"Café ☕ with great food"')
    return owner, target


def test_context_byte_budget_includes_unicode_and_metadata(
    client, fake_llm, dataset, monkeypatch
):
    owner, target = dataset
    assert ask(client, owner, target).status_code == 200
    review = fake_llm.last_request.reviews[0]
    payload = [
        {
            "review_id": str(review.review_id),
            "target_id": str(review.target_id),
            "rating": review.rating,
            "text": review.text,
        }
    ]
    size = len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode())
    monkeypatch.setattr(context, "MAX_CONTEXT_BYTES", size)
    assert ask(client, owner, target).status_code == 200
    monkeypatch.setattr(context, "MAX_CONTEXT_BYTES", size - 1)
    response = ask(client, owner, target)
    assert response.status_code == 422
    assert "smaller dataset" in response.json()["detail"]
    assert len(fake_llm.requests) == 2


def test_record_limit_applies_across_imports_without_silent_sampling(
    client, fake_llm, dataset, monkeypatch
):
    owner, target = dataset
    monkeypatch.setattr(context, "MAX_CONTEXT_REVIEWS", 2)
    ingest(client, owner, target, "rating,review_text\n4,Good service")
    assert ask(client, owner, target).json()["review_count"] == 2
    ingest(client, owner, target, "rating,review_text\n3,Slow service")
    response = ask(client, owner, target)
    assert response.status_code == 422
    assert len(fake_llm.requests) == 1


def test_large_single_review_is_rejected_without_model_call(client, fake_llm, dataset):
    owner, target = dataset
    ingest(
        client,
        owner,
        target,
        "rating,review_text\n4," + "x" * context.MAX_CONTEXT_BYTES,
    )
    assert ask(client, owner, target).status_code == 422
    assert fake_llm.requests == []

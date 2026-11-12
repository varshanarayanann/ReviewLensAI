from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.targets import get_google_maps_source
from app.models.ingestion import IngestionRun, Review
from app.reviews.google_maps import ReviewCollectionError
from tests.test_ingestion_submission import source_targets as source_targets
from tests.test_target_workflow import database as database


@pytest.fixture
def source(client):
    source = SimpleNamespace(
        configured=True,
        collect=Mock(return_value=[{"review_text": "Good coffee", "rating": 5}]),
    )
    client.app.dependency_overrides[get_google_maps_source] = lambda: source
    yield source
    client.app.dependency_overrides.pop(get_google_maps_source, None)


def request_collection(client, headers, target, **body):
    return client.post(
        f"/api/targets/{target}/ingestions/google-maps", headers=headers, json=body
    )


def test_owned_url_is_collected_normalized_and_persisted(
    client, database, source_targets, source
):
    headers, target = source_targets[0]
    source.collect.return_value = [
        {"review_text": "  Good coffee  ", "rating": 5},
        {"review_text": "", "rating": 2},
    ]
    response = request_collection(client, headers, target)
    assert response.status_code == 200
    result = response.json()
    assert (result["state"], result["persisted_count"], result["rejected_count"]) == (
        "partial",
        1,
        1,
    )
    source.collect.assert_called_once_with("https://google.com/maps/place/X")
    with Session(database) as db:
        review = db.scalar(select(Review))
        assert review.target_id == UUID(target)
        assert review.run_id == UUID(result["run_id"])
        assert review.review_text == "Good coffee" and review.rating == 5


def test_denied_targets_and_override_fields_never_contact_provider(
    client, database, source_targets, source
):
    headers, target = source_targets[0]
    other_headers, _ = source_targets[1]
    assert request_collection(client, other_headers, target).status_code == 404
    assert request_collection(client, headers, str(uuid4())).status_code == 404
    assert (
        request_collection(
            client, headers, target, source_url="https://google.com/maps/place/Other"
        ).status_code
        == 422
    )
    source.collect.assert_not_called()
    with Session(database) as db:
        assert db.scalars(select(IngestionRun)).all() == []


@pytest.mark.parametrize("empty", [False, True])
def test_collection_failure_or_empty_result_preserves_previous_reviews(
    client, database, source_targets, source, empty
):
    headers, target = source_targets[0]
    assert request_collection(client, headers, target).json()["state"] == "succeeded"
    if empty:
        source.collect.return_value = []
    else:
        source.collect.side_effect = ReviewCollectionError("secret provider details")
    response = request_collection(client, headers, target)
    assert response.status_code == 200
    assert response.json()["state"] == "failed"
    assert response.json()["persisted_count"] == 0
    assert "secret" not in response.text
    with Session(database) as db:
        assert len(db.scalars(select(Review)).all()) == 1
        assert len(db.scalars(select(IngestionRun)).all()) == 2


def test_missing_configuration_does_not_create_an_attempt(
    client, database, source_targets, source
):
    source.configured = False
    headers, target = source_targets[0]
    assert request_collection(client, headers, target).status_code == 503
    source.collect.assert_not_called()
    with Session(database) as db:
        assert db.scalars(select(IngestionRun)).all() == []

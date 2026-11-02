from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Base
from app.models.ingestion import IngestionRun, Review
from tests.conftest import USER_A_ID
from tests.test_target_workflow import database as database  # Shared DB fixture.

CSV = "rating,review_text\n5,Great"
USER_B_ID = "22222222-2222-4222-8222-222222222222"


@pytest.fixture
def source_targets(client, make_token, database):
    with database.begin() as connection:
        connection.execute(
            Base.metadata.tables["auth.users"].insert().values(id=UUID(USER_B_ID))
        )
    targets = []
    for subject in (USER_A_ID, USER_B_ID):
        headers = {"Authorization": f"Bearer {make_token(sub=subject)}"}
        created = client.post(
            "/api/targets",
            headers=headers,
            json={
                "name": "Source target",
                "source_url": "https://google.com/maps/place/X",
            },
        )
        assert created.status_code == 201
        targets.append((headers, created.json()["id"]))
    return targets


def stored_rows(database):
    with database.connect() as connection:
        return {
            name: connection.execute(
                select(Base.metadata.tables[name]).order_by(
                    Base.metadata.tables[name].c.id
                )
            ).all()
            for name in ("analysis_targets", "reviews", "ingestion_runs")
        }


def test_each_user_can_submit_only_to_their_existing_target(
    client, database, source_targets
):
    for headers, target in source_targets:
        response = client.post(
            f"/api/targets/{target}/ingestions",
            headers=headers,
            json={
                "csv_text": "\ufeffrating,review_text,reviewer_name\n5, Great ,Person"
            },
        )
        assert response.status_code == 200
        outcome = response.json()
        assert outcome["target_id"] == target
        assert outcome["state"] == "succeeded" and outcome["persisted_count"] == 1
        with Session(database) as db:
            run = db.get(IngestionRun, UUID(outcome["run_id"]))
            review = db.scalar(select(Review).where(Review.run_id == run.id))
            assert run.target_id == review.target_id == UUID(target)
            assert review.review_text == "Great" and review.rating == 5


@pytest.mark.parametrize("unknown", [False, True])
def test_denial_happens_before_source_parsing_or_attempt_creation(
    client, database, source_targets, monkeypatch, unknown
):
    before = stored_rows(database)

    def forbidden_parser(*args, **kwargs):
        pytest.fail("Unauthorized or missing targets must not parse CSV")

    monkeypatch.setattr("app.api.targets.csv.DictReader", forbidden_parser)
    for index, (headers, _) in enumerate(source_targets):
        target = str(uuid4()) if unknown else source_targets[1 - index][1]
        response = client.post(
            f"/api/targets/{target}/ingestions", headers=headers, json={"csv_text": CSV}
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Analysis target not found."}
    assert stored_rows(database) == before


@pytest.mark.parametrize("token", [None, "invalid-token"])
def test_authentication_is_required_before_processing(
    client, database, source_targets, monkeypatch, token
):
    def forbidden_parser(*args, **kwargs):
        pytest.fail("Unauthenticated requests must not parse CSV")

    monkeypatch.setattr("app.api.targets.csv.DictReader", forbidden_parser)
    before = stored_rows(database)
    headers = {"X-User-Id": USER_A_ID}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    response = client.post(
        f"/api/targets/{source_targets[0][1]}/ingestions",
        headers=headers,
        json={"csv_text": CSV},
    )
    assert response.status_code == 401
    assert stored_rows(database) == before


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"csv_text": ""},
        {"csv_text": None},
        {"csv_text": 123},
        {"csv_text": CSV, "owner_id": USER_B_ID},
        {"csv_text": CSV, "target_id": USER_B_ID},
        {"source_url": "https://google.com/maps/place/X"},
    ],
)
def test_required_source_contract_rejects_invalid_requests_without_changes(
    client, database, source_targets, payload
):
    before = stored_rows(database)
    headers, target = source_targets[0]
    response = client.post(
        f"/api/targets/{target}/ingestions", headers=headers, json=payload
    )
    assert response.status_code == 422
    assert stored_rows(database) == before


@pytest.mark.parametrize(
    "csv_text",
    [
        "   \n",
        "\ufeff",
        "rating,review_text\n",
        "rating,text\n5,Private source",
        "rating,rating,review_text\n5,1,Private source",
        "rating,review_text\n5,Private source,extra",
        'rating,review_text\n5,"Private source',
        "rating,review_text\n" + "5,Great\n" * 1001,
        "rating,review_text\n5," + "é" * 500_000,
    ],
    ids=[
        "whitespace",
        "bom-only",
        "header-only",
        "missing-column",
        "duplicate-column",
        "extra-field",
        "broken-quote",
        "too-many-rows",
        "utf8-size-limit",
    ],
)
def test_missing_or_unusable_source_is_rejected_before_recording_attempt(
    client, database, source_targets, csv_text
):
    before = stored_rows(database)
    headers, target = source_targets[0]
    response = client.post(
        f"/api/targets/{target}/ingestions",
        headers=headers,
        json={"csv_text": csv_text},
    )
    assert response.status_code == 422
    assert response.json() == {
        "detail": "Provide a CSV with rating and review_text columns and 1–1,000 "
        "reviews (maximum 1 MB)."
    }
    assert "Private source" not in response.text
    assert stored_rows(database) == before


def test_source_failure_preserves_prior_reviews_and_latest_result(
    client, database, source_targets
):
    headers, target = source_targets[0]
    path = f"/api/targets/{target}/ingestions"
    saved = client.post(path, headers=headers, json={"csv_text": CSV})
    assert saved.json()["state"] == "succeeded"
    before = stored_rows(database)
    rejected = client.post(
        path, headers=headers, json={"csv_text": "no,columns\n5,Text"}
    )
    assert rejected.status_code == 422
    assert client.get(path + "/latest", headers=headers).json() == saved.json()
    assert stored_rows(database) == before


def test_maximum_review_count_is_accepted(client, database, source_targets):
    headers, target = source_targets[0]
    response = client.post(
        f"/api/targets/{target}/ingestions",
        headers=headers,
        json={"csv_text": "rating,review_text\n" + "5,Great\n" * 1000},
    )
    assert response.status_code == 200
    assert response.json()["state"] == "succeeded"
    assert response.json()["persisted_count"] == 1000

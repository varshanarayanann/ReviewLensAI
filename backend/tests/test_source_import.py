from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ingestion import IngestionRun, Review
from app.reviews.csv_source import ReviewSourceError
from tests.test_target_workflow import database as database  # Shared DB fixture.

FIXTURE = Path(__file__).parent / "fixtures" / "google_maps_export.csv"


def create_target(client, make_token):
    headers = {"Authorization": f"Bearer {make_token()}"}
    response = client.post(
        "/api/targets",
        headers=headers,
        json={"name": "Export target", "source_url": "https://google.com/maps/place/X"},
    )
    assert response.status_code == 201
    return headers, response.json()["id"]


def test_submitted_export_is_persisted_without_replacement(
    client, make_token, database
):
    headers, target = create_target(client, make_token)
    path = f"/api/targets/{target}/ingestions"
    imported = client.post(
        path, headers=headers, json={"csv_text": FIXTURE.read_text(encoding="utf-8")}
    )
    assert imported.status_code == 200
    assert imported.json()["state"] == "succeeded"
    assert imported.json()["persisted_count"] == 3
    with Session(database) as db:
        rows = db.scalars(select(Review)).all()
        assert {(row.rating, row.review_text) for row in rows} == {
            (5, "Fixture café review, with a comma."),
            (2, "Fixture first line.\nFixture second line."),
            (4, 'Fixture says "thank you" — ありがとう.'),
        }
        assert {row.target_id for row in rows} == {UUID(target)}
        assert len({row.id for row in rows}) == 3
    rejected = client.post(
        path, headers=headers, json={"csv_text": "not,a,review-export"}
    )
    assert rejected.status_code == 422
    assert client.get(path + "/latest", headers=headers).json() == imported.json()
    with Session(database) as db:
        assert len(db.scalars(select(Review)).all()) == 3
        assert len(db.scalars(select(IngestionRun)).all()) == 1


def test_other_users_and_missing_targets_never_call_adapter(
    client, make_token, database, monkeypatch
):
    _, target = create_target(client, make_token)

    def forbidden_source(*args, **kwargs):
        pytest.fail("Denied requests must not obtain or parse source data")

    monkeypatch.setattr("app.api.targets.parse_csv_reviews", forbidden_source)
    other = {"Authorization": f"Bearer {make_token(sub=str(uuid4()))}"}
    for target_id in (target, str(uuid4())):
        response = client.post(
            f"/api/targets/{target_id}/ingestions",
            headers=other,
            json={"csv_text": "rating,review_text\n5,Denied"},
        )
        assert response.status_code == 404
    with Session(database) as db:
        assert not db.scalars(select(IngestionRun)).all()
        assert not db.scalars(select(Review)).all()


def test_source_failure_is_safe_and_never_falls_back_to_fixture(
    client, make_token, database, monkeypatch
):
    headers, target = create_target(client, make_token)

    def broken_source(*args, **kwargs):
        raise ReviewSourceError("Private review text / internal parser detail")

    monkeypatch.setattr("app.api.targets.parse_csv_reviews", broken_source)
    response = client.post(
        f"/api/targets/{target}/ingestions",
        headers=headers,
        json={"csv_text": "rating,review_text\n5,Actual submitted text"},
    )
    assert response.status_code == 422
    assert "Private" not in response.text and "Fixture" not in response.text
    with Session(database) as db:
        assert not db.scalars(select(Review)).all()
        assert not db.scalars(select(IngestionRun)).all()

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisTarget, QuestionExchange
from app.models.ingestion import Review
from app.schemas.analysis_target import AnalysisTargetUpdate
from tests.test_ingestion_submission import source_targets as source_targets
from tests.test_ingestion_submission import stored_rows
from tests.test_target_workflow import database as database


@pytest.mark.parametrize("name", [None, "", "   ", "x" * 121])
def test_rename_rejects_unusable_names(name):
    with pytest.raises(ValidationError):
        AnalysisTargetUpdate(name=name)


def test_rename_trims_name():
    assert AnalysisTargetUpdate(name="  Hapive Coffee  ").name == "Hapive Coffee"


def test_rename_requires_authentication(client):
    response = client.patch(f"/api/targets/{uuid4()}", json={"name": "Renamed"})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_owner_can_rename_without_changing_source_or_reviews(
    client, database, source_targets
):
    owner, target = source_targets[0]
    before = client.get(f"/api/targets/{target}", headers=owner).json()
    ingest = client.post(
        f"/api/targets/{target}/ingestions",
        headers=owner,
        json={"csv_text": "rating,review_text\n5,Great coffee"},
    )
    assert ingest.status_code == 200
    rows_before = stored_rows(database)

    response = client.patch(
        f"/api/targets/{target}", headers=owner, json={"name": "  Downtown Cafe  "}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == target
    assert body["name"] == "Downtown Cafe"
    assert body["platform"] == "google_maps"
    assert body["source_url"] == before["source_url"]

    with Session(database) as db:
        saved = db.get(AnalysisTarget, UUID(target))
        assert saved is not None
        assert saved.name == "Downtown Cafe"
        assert saved.source_url == before["source_url"]
        assert (
            db.query(Review).filter(Review.target_id == UUID(target)).count() == 1
        )
    assert stored_rows(database)["reviews"] == rows_before["reviews"]


def test_owner_can_rename_without_changing_qa_history(
    client, database, source_targets
):
    """S3-002: rename updates the display name only; Q&A rows stay intact."""
    owner, target = source_targets[0]
    before = client.get(f"/api/targets/{target}", headers=owner).json()
    assert (
        client.post(
            f"/api/targets/{target}/ingestions",
            headers=owner,
            json={"csv_text": "rating,review_text\n5,Great coffee"},
        ).status_code
        == 200
    )
    with Session(database) as db:
        db.add(
            QuestionExchange(
                target_id=UUID(target),
                question="How is the coffee?",
                answer="Customers say it's great.",
                status="answered",
                review_count=1,
            )
        )
        db.commit()
    history_before = client.get(
        f"/api/targets/{target}/questions", headers=owner
    ).json()
    assert len(history_before) == 1

    response = client.patch(
        f"/api/targets/{target}", headers=owner, json={"name": "Renamed Cafe"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Renamed Cafe"
    assert body["source_url"] == before["source_url"]
    assert (
        client.get(f"/api/targets/{target}/questions", headers=owner).json()
        == history_before
    )

    with Session(database) as db:
        rows = db.scalars(
            select(QuestionExchange).where(QuestionExchange.target_id == UUID(target))
        ).all()
        assert len(rows) == 1
        assert rows[0].question == "How is the coffee?"
        assert rows[0].answer == "Customers say it's great."
        assert rows[0].status == "answered"
        assert (
            db.query(Review).filter(Review.target_id == UUID(target)).count() == 1
        )


def test_rename_rejects_source_url_and_owner_fields(client, source_targets):
    owner, target = source_targets[0]
    response = client.patch(
        f"/api/targets/{target}",
        headers=owner,
        json={
            "name": "Hacked",
            "source_url": "https://www.google.com/maps/place/Other",
            "owner_id": str(uuid4()),
        },
    )
    assert response.status_code == 422
    current = client.get(f"/api/targets/{target}", headers=owner).json()
    assert current["name"] != "Hacked"


def test_missing_and_other_users_targets_share_safe_denial(
    client, database, source_targets
):
    owner, target = source_targets[0]
    other_owner, _ = source_targets[1]
    before = stored_rows(database)
    denied = client.patch(
        f"/api/targets/{target}", headers=other_owner, json={"name": "Stolen"}
    )
    missing = client.patch(
        f"/api/targets/{uuid4()}", headers=other_owner, json={"name": "Missing"}
    )
    assert denied.status_code == missing.status_code == 404
    assert denied.json() == missing.json() == {"detail": "Analysis target not found."}
    assert stored_rows(database) == before
    renamed = client.get(f"/api/targets/{target}", headers=owner).json()
    assert renamed["name"] != "Stolen"

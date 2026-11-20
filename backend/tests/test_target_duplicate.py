from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models import AnalysisTarget, QuestionExchange
from app.schemas.analysis_target import AnalysisTargetCopy
from tests.test_ingestion_submission import source_targets as source_targets
from tests.test_ingestion_submission import stored_rows
from tests.test_target_workflow import database as database


def seed_reviews(client, headers, target, csv_text="rating,review_text\n5,Great coffee"):
    response = client.post(
        f"/api/targets/{target}/ingestions",
        headers=headers,
        json={"csv_text": csv_text},
    )
    assert response.status_code == 200
    return response.json()


def seed_qa(database, target_id: str, question="How is the coffee?", answer="Great."):
    with Session(database) as db:
        db.add(
            QuestionExchange(
                target_id=UUID(target_id),
                question=question,
                answer=answer,
                status="answered",
                review_count=1,
            )
        )
        db.commit()


@pytest.mark.parametrize("name", [None, "", "   ", "x" * 121])
def test_copy_rejects_unusable_names(name):
    with pytest.raises(ValidationError):
        AnalysisTargetCopy(name=name)


def test_copy_trims_name():
    assert AnalysisTargetCopy(name="  Hapive Coffee copy  ").name == "Hapive Coffee copy"


def test_copy_requires_authentication(client):
    response = client.post(f"/api/targets/{uuid4()}/copies", json={"name": "Copy"})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_save_as_creates_independent_copy_with_reviews_and_qa(
    client, database, source_targets
):
    owner, target = source_targets[0]
    source = client.get(f"/api/targets/{target}", headers=owner).json()
    seed_reviews(client, owner, target)
    seed_qa(database, target)
    source_history = client.get(f"/api/targets/{target}/questions", headers=owner).json()
    source_reviews = client.get(f"/api/targets/{target}/reviews", headers=owner).json()
    before = stored_rows(database)

    response = client.post(
        f"/api/targets/{target}/copies",
        headers=owner,
        json={"name": "  Hapive Coffee copy  "},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"] != target
    assert body["name"] == "Hapive Coffee copy"
    assert body["platform"] == "google_maps"
    assert body["source_url"] == source["source_url"]

    copy_id = body["id"]
    copy_reviews = client.get(f"/api/targets/{copy_id}/reviews", headers=owner).json()
    assert len(copy_reviews) == len(source_reviews) == 1
    assert copy_reviews[0]["id"] != source_reviews[0]["id"]
    assert copy_reviews[0]["review_text"] == source_reviews[0]["review_text"]
    assert copy_reviews[0]["rating"] == source_reviews[0]["rating"]
    assert copy_reviews[0]["target_id"] == copy_id

    copy_history = client.get(f"/api/targets/{copy_id}/questions", headers=owner).json()
    assert len(copy_history) == 1
    assert copy_history[0]["id"] != source_history[0]["id"]
    assert copy_history[0]["question"] == source_history[0]["question"]
    assert copy_history[0]["answer"] == source_history[0]["answer"]
    assert copy_history[0]["target_id"] == copy_id
    assert (
        client.get(f"/api/targets/{target}/questions", headers=owner).json()
        == source_history
    )
    assert (
        client.get(f"/api/targets/{target}/reviews", headers=owner).json()
        == source_reviews
    )

    after = stored_rows(database)
    assert len(after["analysis_targets"]) == len(before["analysis_targets"]) + 1
    assert len(after["reviews"]) == len(before["reviews"]) + 1
    assert len(after["ingestion_runs"]) == len(before["ingestion_runs"]) + 1


def test_save_as_empty_source_creates_empty_copy(client, database, source_targets):
    owner, target = source_targets[0]
    response = client.post(
        f"/api/targets/{target}/copies",
        headers=owner,
        json={"name": "Empty copy"},
    )
    assert response.status_code == 201
    copy_id = response.json()["id"]
    assert client.get(f"/api/targets/{copy_id}/reviews", headers=owner).json() == []
    assert client.get(f"/api/targets/{copy_id}/questions", headers=owner).json() == []
    assert (
        client.get(f"/api/targets/{copy_id}/ingestions/latest", headers=owner).json()
        is None
    )


def test_renaming_copy_does_not_rename_original(client, database, source_targets):
    owner, target = source_targets[0]
    original_name = client.get(f"/api/targets/{target}", headers=owner).json()["name"]
    copy_id = client.post(
        f"/api/targets/{target}/copies", headers=owner, json={"name": "Copy"}
    ).json()["id"]
    assert (
        client.patch(
            f"/api/targets/{copy_id}", headers=owner, json={"name": "Renamed copy"}
        ).status_code
        == 200
    )
    assert (
        client.get(f"/api/targets/{target}", headers=owner).json()["name"]
        == original_name
    )
    assert (
        client.get(f"/api/targets/{copy_id}", headers=owner).json()["name"]
        == "Renamed copy"
    )


def test_deleting_copy_does_not_delete_original(client, database, source_targets):
    owner, target = source_targets[0]
    seed_reviews(client, owner, target)
    seed_qa(database, target)
    copy_id = client.post(
        f"/api/targets/{target}/copies", headers=owner, json={"name": "Copy"}
    ).json()["id"]
    assert client.delete(f"/api/targets/{copy_id}", headers=owner).status_code == 204
    assert client.get(f"/api/targets/{target}", headers=owner).status_code == 200
    assert len(client.get(f"/api/targets/{target}/reviews", headers=owner).json()) == 1
    assert len(client.get(f"/api/targets/{target}/questions", headers=owner).json()) == 1
    with Session(database) as db:
        assert db.get(AnalysisTarget, UUID(copy_id)) is None
        assert db.get(AnalysisTarget, UUID(target)) is not None


def test_reingesting_copy_does_not_mutate_original(client, database, source_targets):
    owner, target = source_targets[0]
    seed_reviews(client, owner, target, "rating,review_text\n5,Original only")
    copy_id = client.post(
        f"/api/targets/{target}/copies", headers=owner, json={"name": "Copy"}
    ).json()["id"]
    source_before = client.get(f"/api/targets/{target}/reviews", headers=owner).json()
    seed_reviews(client, owner, copy_id, "rating,review_text\n4,Only on copy")
    assert (
        client.get(f"/api/targets/{target}/reviews", headers=owner).json()
        == source_before
    )
    copy_reviews = client.get(f"/api/targets/{copy_id}/reviews", headers=owner).json()
    assert len(copy_reviews) == 2
    assert {row["review_text"] for row in copy_reviews} == {
        "Original only",
        "Only on copy",
    }


def test_missing_and_other_users_targets_share_safe_denial(
    client, database, source_targets
):
    owner, target = source_targets[0]
    other_owner, _ = source_targets[1]
    seed_reviews(client, owner, target)
    before = stored_rows(database)
    denied = client.post(
        f"/api/targets/{target}/copies", headers=other_owner, json={"name": "Stolen"}
    )
    missing = client.post(
        f"/api/targets/{uuid4()}/copies", headers=other_owner, json={"name": "Missing"}
    )
    assert denied.status_code == missing.status_code == 404
    assert denied.json() == missing.json() == {"detail": "Analysis target not found."}
    assert stored_rows(database) == before
    listed = client.get("/api/targets", headers=other_owner).json()
    assert all(item["id"] != target for item in listed)


def test_copy_rejects_source_url_and_owner_fields(client, source_targets):
    owner, target = source_targets[0]
    response = client.post(
        f"/api/targets/{target}/copies",
        headers=owner,
        json={
            "name": "Hacked",
            "source_url": "https://www.google.com/maps/place/Other",
            "owner_id": str(uuid4()),
        },
    )
    assert response.status_code == 422

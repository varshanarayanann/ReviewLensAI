from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models import AnalysisTarget, QuestionExchange
from app.models.ingestion import IngestionRun
from tests.test_ingestion_submission import source_targets as source_targets
from tests.test_ingestion_submission import stored_rows
from tests.test_target_workflow import database as database


def seed_reviews(client, headers, target):
    response = client.post(
        f"/api/targets/{target}/ingestions",
        headers=headers,
        json={"csv_text": "rating,review_text\n5,Great"},
    )
    assert response.status_code == 200
    return response.json()


def seed_qa(database, target_id: str, question: str):
    with Session(database) as db:
        db.add(
            QuestionExchange(
                target_id=UUID(target_id),
                question=question,
                answer="Saved answer",
                status="answered",
                review_count=1,
            )
        )
        db.commit()


def history_target_ids(database):
    with Session(database) as db:
        return {
            str(row) for row in db.scalars(select(QuestionExchange.target_id)).all()
        }


def test_delete_requires_authentication_before_database_access(client):
    response = client.delete(f"/api/targets/{uuid4()}")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_delete_empty_owned_target(client, database, source_targets):
    owner, target = source_targets[0]
    response = client.delete(f"/api/targets/{target}", headers=owner)
    assert response.status_code == 204
    with Session(database) as db:
        assert db.get(AnalysisTarget, UUID(target)) is None


def test_delete_removes_only_owned_target_and_children(
    client, database, source_targets
):
    owner, target = source_targets[0]
    other_owner, other_target = source_targets[1]
    seed_reviews(client, owner, target)
    seed_reviews(client, other_owner, other_target)
    before = stored_rows(database)
    response = client.delete(f"/api/targets/{target}", headers=owner)
    assert response.status_code == 204 and response.content == b""
    after = stored_rows(database)
    for name in after:
        assert len(after[name]) == len(before[name]) - 1
    assert str(after["analysis_targets"][0].id) == other_target
    assert str(after["reviews"][0].target_id) == other_target
    assert str(after["ingestion_runs"][0].target_id) == other_target
    assert client.get(f"/api/targets/{target}", headers=owner).status_code == 404
    assert client.delete(f"/api/targets/{target}", headers=owner).status_code == 404


def test_delete_clears_qa_history_for_target_and_leaves_others(
    client, database, source_targets
):
    """S3-005: cascading delete removes this target's Q&A only."""
    owner, target = source_targets[0]
    other_owner, other_target = source_targets[1]
    seed_reviews(client, owner, target)
    seed_reviews(client, other_owner, other_target)
    seed_qa(database, target, "Deleted target question")
    seed_qa(database, other_target, "Other target question")
    assert history_target_ids(database) == {target, other_target}

    response = client.delete(f"/api/targets/{target}", headers=owner)
    assert response.status_code == 204
    assert history_target_ids(database) == {other_target}
    questions = client.get(f"/api/targets/{target}/questions", headers=owner)
    assert questions.status_code == 404
    remaining = client.get(
        f"/api/targets/{other_target}/questions", headers=other_owner
    ).json()
    assert len(remaining) == 1
    assert remaining[0]["question"] == "Other target question"
    assert remaining[0]["target_id"] == other_target


def test_missing_and_other_users_targets_share_safe_denial(
    client, database, source_targets
):
    owner, target = source_targets[0]
    other_owner, _ = source_targets[1]
    seed_reviews(client, owner, target)
    before = stored_rows(database)
    denied = client.delete(f"/api/targets/{target}", headers=other_owner)
    missing = client.delete(f"/api/targets/{uuid4()}", headers=other_owner)
    assert denied.status_code == missing.status_code == 404
    assert denied.json() == missing.json()
    assert stored_rows(database) == before


@pytest.mark.parametrize("age,expected_status", [(0, 409), (10, 204)])
def test_active_collection_blocks_delete_but_abandoned_run_can_be_cleaned(
    client, database, source_targets, age, expected_status
):
    owner, target = source_targets[0]
    with Session(database) as db:
        db.add(
            IngestionRun(
                target_id=UUID(target),
                state="processing",
                created_at=datetime.now(UTC) - timedelta(minutes=age),
            )
        )
        db.commit()
    before = stored_rows(database)
    response = client.delete(f"/api/targets/{target}", headers=owner)
    assert response.status_code == expected_status
    if expected_status == 409:
        assert stored_rows(database) == before
    else:
        with Session(database) as db:
            assert db.get(AnalysisTarget, UUID(target)) is None


@pytest.mark.parametrize("rollback_fails", [False, True])
def test_failed_delete_rolls_back_all_records_with_safe_error(
    client, database, source_targets, monkeypatch, rollback_fails, caplog
):
    owner, target = source_targets[0]
    seed_reviews(client, owner, target)
    before = stored_rows(database)

    def fail(*args, **kwargs):
        raise OperationalError("secret SQL", {}, RuntimeError("private DB details"))

    monkeypatch.setattr(Session, "commit", fail)
    if rollback_fails:
        monkeypatch.setattr(Session, "rollback", fail)
    response = client.delete(f"/api/targets/{target}", headers=owner)
    assert response.status_code == 503
    assert "secret SQL" not in response.text + caplog.text
    assert "private DB details" not in response.text + caplog.text
    assert stored_rows(database) == before

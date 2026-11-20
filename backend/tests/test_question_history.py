from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models import QuestionExchange
from app.qa import context
from app.qa.llm import LLMResponse, LLMUnavailableError, ReplyOutcome
from tests.test_ingestion_submission import source_targets as source_targets
from tests.test_ingestion_submission import stored_rows
from tests.test_target_workflow import database as database


def ask(client, owner, target, question="What do reviewers say?"):
    return client.post(
        f"/api/targets/{target}/questions", headers=owner, json={"question": question}
    )


def history(client, owner, target, **params):
    return client.get(f"/api/targets/{target}/questions", headers=owner, params=params)


def rows(database):
    with Session(database) as db:
        return db.scalars(select(QuestionExchange)).all()


def seed(client, owner, target):
    response = client.post(
        f"/api/targets/{target}/ingestions",
        headers=owner,
        json={"csv_text": "rating,review_text\n5,Great battery life"},
    )
    assert response.status_code == 200


@pytest.mark.parametrize("outcome", list(ReplyOutcome))
def test_completed_reply_is_durable_and_reconstructable(
    client, database, source_targets, fake_llm, outcome
):
    owner, target = source_targets[0]
    seed(client, owner, target)
    question, answer = "What about battery life? ☕", "Saved reply with café details."
    fake_llm.respond_with(LLMResponse(outcome, answer))
    started = datetime.now(UTC)
    response = ask(client, owner, target, f"  {question}  ")
    assert response.status_code == 200
    # A new connection verifies persistence, not an ORM identity-map value.
    saved = rows(database)
    assert len(saved) == 1
    assert saved[0].target_id == UUID(target)
    restored = history(client, owner, target).json()
    assert len(restored) == 1
    record = restored[0]
    assert UUID(record["id"]) == saved[0].id
    assert record["question"] == question
    assert record["answer"] == answer
    assert record["status"] == outcome.value
    assert record["review_count"] == 1
    assert record["target_id"] == target
    assert started <= datetime.fromisoformat(record["created_at"]) <= datetime.now(UTC)
    assert {key: record[key] for key in response.json()} == response.json()


def test_empty_target_saves_explicit_no_reviews_without_model(
    client, database, source_targets, fake_llm
):
    owner, target = source_targets[0]
    assert history(client, owner, target).json() == []
    assert ask(client, owner, target).status_code == 200
    saved = history(client, owner, target).json()[0]
    assert saved["status"] == "no_reviews"
    assert saved["answer"] is None and saved["review_count"] == 0
    assert fake_llm.requests == []


def test_history_is_scoped_to_owner_and_active_target_and_not_sent_to_model(
    client, database, source_targets, fake_llm
):
    for index, (owner, target) in enumerate(source_targets):
        seed(client, owner, target)
        fake_llm.respond_with(f"Private answer {index}")
        assert (
            ask(client, owner, target, f"Private question {index}").status_code == 200
        )
    owner, target = source_targets[0]
    another = client.post(
        "/api/targets",
        headers=owner,
        json={"name": "Another", "source_url": "https://google.com/maps/place/X"},
    ).json()["id"]
    assert history(client, owner, another).json() == []
    for index, (headers, target_id) in enumerate(source_targets):
        saved = history(client, headers, target_id).json()
        assert len(saved) == 1
        assert saved[0]["question"] == f"Private question {index}"
        assert saved[0]["answer"] == f"Private answer {index}"
    assert ask(client, owner, target, "A fresh question").status_code == 200
    request = fake_llm.last_request
    assert request.question == "A fresh question"
    assert "Private question" not in request.system_prompt
    assert "Private answer" not in request.system_prompt
    assert [review.text for review in request.reviews] == ["Great battery life"]


def test_denied_and_invalid_requests_never_save_or_call_model(
    client, database, source_targets, fake_llm
):
    owner, target = source_targets[0]
    other, _ = source_targets[1]
    for inaccessible in (target, str(uuid4())):
        assert history(client, other, inaccessible).status_code == 404
        assert ask(client, other, inaccessible).status_code == 404
    for body in ({"question": ""}, {"question": "x", "owner_id": str(uuid4())}):
        assert (
            client.post(
                f"/api/targets/{target}/questions", headers=owner, json=body
            ).status_code
            == 422
        )
    assert history(client, owner, target, limit=101).status_code == 422
    assert history(client, owner, target, offset=-1).status_code == 422
    assert rows(database) == [] and fake_llm.requests == []


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_history_requires_authentication(client, method):
    response = client.request(
        method, f"/api/targets/{uuid4()}/questions", json={"question": "Hello"}
    )
    assert response.status_code == 401


def test_pagination_has_stable_timestamp_and_uuid_order(
    client, database, source_targets
):
    owner, target = source_targets[0]
    for question in ("First", "Second", "Third"):
        assert ask(client, owner, target, question).status_code == 200
    with Session(database) as db:
        # Ties use the immutable ID, not unspecified database row ordering.
        db.execute(
            update(QuestionExchange).values(created_at=datetime(2026, 1, 1, tzinfo=UTC))
        )
        db.commit()
    all_rows = history(client, owner, target).json()
    assert [row["id"] for row in all_rows] == sorted(row["id"] for row in all_rows)
    assert history(client, owner, target, limit=1, offset=1).json() == all_rows[1:2]
    assert history(client, owner, target, offset=3).json() == []


def test_provider_failure_and_context_overflow_preserve_existing_history(
    client, database, source_targets, fake_llm, monkeypatch
):
    owner, target = source_targets[0]
    seed(client, owner, target)
    assert ask(client, owner, target).status_code == 200
    before = history(client, owner, target).json()
    fake_llm.respond_with(LLMUnavailableError("private provider payload"))
    assert ask(client, owner, target).status_code == 503
    monkeypatch.setattr(context, "MAX_CONTEXT_REVIEWS", 0)
    assert ask(client, owner, target).status_code == 422
    assert history(client, owner, target).json() == before


@pytest.mark.parametrize("rollback_fails", [False, True])
def test_failed_commit_is_safe_and_does_not_leave_partial_history(
    client, database, source_targets, monkeypatch, caplog, rollback_fails
):
    owner, target = source_targets[0]
    assert ask(client, owner, target, "Already saved").status_code == 200
    before = history(client, owner, target).json()

    def fail(*args, **kwargs):
        raise OperationalError("secret SQL", {}, RuntimeError("private question"))

    with monkeypatch.context() as patch:

        def fail_after_flush(db):
            db.flush()
            fail()

        patch.setattr(Session, "commit", fail_after_flush)
        if rollback_fails:
            patch.setattr(Session, "rollback", fail)
        response = ask(client, owner, target, "private question")
    assert response.status_code == 503
    assert "secret SQL" not in response.text + caplog.text
    assert "private question" not in response.text + caplog.text
    assert history(client, owner, target).json() == before


def test_history_read_failure_is_safe(client, database, source_targets, monkeypatch):
    owner, target = source_targets[0]

    def fail(*args, **kwargs):
        raise OperationalError("private query", {}, RuntimeError())

    monkeypatch.setattr(Session, "scalars", fail)
    response = history(client, owner, target)
    assert response.status_code == 503 and "private query" not in response.text


def test_deleting_target_removes_only_its_history(client, database, source_targets):
    for owner, target in source_targets:
        assert ask(client, owner, target).status_code == 200
    before = stored_rows(database)
    owner, target = source_targets[0]
    other, other_target = source_targets[1]
    assert client.delete(f"/api/targets/{target}", headers=owner).status_code == 204
    assert history(client, owner, target).status_code == 404
    assert len(history(client, other, other_target).json()) == 1
    assert len(rows(database)) == 1
    assert (
        len(stored_rows(database)["analysis_targets"])
        == len(before["analysis_targets"]) - 1
    )


def test_postgres_history_table_enables_rls(database):
    if database.dialect.name != "postgresql":
        pytest.skip("PostgreSQL RLS integration")
    with database.connect() as connection:
        assert (
            connection.scalar(
                text(
                    "SELECT relrowsecurity FROM pg_class "
                    "WHERE oid = 'question_exchanges'::regclass"
                )
            )
            is True
        )

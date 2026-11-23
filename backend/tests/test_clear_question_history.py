from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models import QuestionExchange
from tests.conftest import USER_A_ID
from tests.test_ingestion_submission import source_targets as source_targets
from tests.test_ingestion_submission import stored_rows
from tests.test_target_workflow import database as database


def history_rows(database):
    with database.connect() as connection:
        return connection.execute(
            select(QuestionExchange).order_by(QuestionExchange.id)
        ).all()


def ask(client, owner, target, question="What about battery life?"):
    return client.post(
        f"/api/targets/{target}/questions", headers=owner, json={"question": question}
    )


@pytest.fixture
def populated(client, database, source_targets):
    for owner, target in source_targets:
        assert (
            client.post(
                f"/api/targets/{target}/ingestions",
                headers=owner,
                json={"csv_text": "rating,review_text\n5,Great battery life"},
            ).status_code
            == 200
        )
        assert ask(client, owner, target).status_code == 200
    return source_targets


def test_clear_all_history_preserves_analysis_reviews_runs_and_other_histories(
    client, database, populated, fake_llm
):
    owner, target = populated[0]
    other_owner, other_target = populated[1]
    another = client.post(
        "/api/targets",
        headers=owner,
        json={
            "name": "Another analysis",
            "source_url": "https://google.com/maps/place/Other",
        },
    ).json()["id"]
    assert ask(client, owner, another).status_code == 200
    with Session(database) as db:
        db.add_all(
            [
                QuestionExchange(
                    target_id=UUID(target),
                    question=f"Saved {index}",
                    answer="Saved answer",
                    status="answered",
                    review_count=1,
                )
                for index in range(101)
            ]
        )
        db.commit()
    before = stored_rows(database)
    path = f"/api/targets/{target}"
    resources = {
        suffix: client.get(path + suffix, headers=owner).json()
        for suffix in ("", "/reviews", "/reviews/summary", "/ingestions/latest")
    }
    calls = len(fake_llm.requests)
    response = client.delete(path + "/questions", headers=owner)
    assert response.status_code == 204 and response.content == b""
    assert client.get(path + "/questions", headers=owner).json() == []
    assert stored_rows(database) == before
    for suffix, expected in resources.items():
        assert client.get(path + suffix, headers=owner).json() == expected
    remaining = history_rows(database)
    assert len(remaining) == 2
    assert {row.target_id for row in remaining} == {UUID(other_target), UUID(another)}
    assert (
        len(
            client.get(
                f"/api/targets/{other_target}/questions", headers=other_owner
            ).json()
        )
        == 1
    )
    assert len(fake_llm.requests) == calls
    assert client.delete(path + "/questions", headers=owner).status_code == 204


def test_cleared_analysis_can_answer_again_using_its_unchanged_dataset(
    client, database, populated, fake_llm
):
    owner, target = populated[0]
    path = f"/api/targets/{target}/questions"
    assert client.delete(path, headers=owner).status_code == 204
    fake_llm.respond_with("A new answer about the same battery reviews.")
    assert ask(client, owner, target, "A fresh question").status_code == 200
    restored = client.get(path, headers=owner).json()
    assert [row["question"] for row in restored] == ["A fresh question"]
    assert [review.text for review in fake_llm.last_request.reviews] == [
        "Great battery life"
    ]


def test_denied_clear_has_no_effect_even_with_spoofed_owner(
    client, database, populated
):
    _, target = populated[0]
    other, _ = populated[1]
    before, saved = stored_rows(database), history_rows(database)
    denied = client.delete(
        f"/api/targets/{target}/questions",
        headers={**other, "X-Owner-Id": USER_A_ID},
        params={"owner_id": USER_A_ID},
    )
    missing = client.delete(f"/api/targets/{uuid4()}/questions", headers=other)
    assert denied.status_code == missing.status_code == 404
    assert denied.json() == missing.json()
    assert stored_rows(database) == before
    assert history_rows(database) == saved


def test_clear_requires_authentication(client):
    assert client.delete(f"/api/targets/{uuid4()}/questions").status_code == 401


@pytest.mark.parametrize("rollback_fails", [False, True])
def test_failed_clear_rolls_back_and_logs_only_safe_diagnostics(
    client, database, populated, monkeypatch, caplog, rollback_fails
):
    owner, target = populated[0]
    before, saved = stored_rows(database), history_rows(database)

    def fail(*args, **kwargs):
        raise OperationalError("private SQL", {}, RuntimeError("private answer"))

    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", fail)
        if rollback_fails:
            patch.setattr(Session, "rollback", fail)
        response = client.delete(f"/api/targets/{target}/questions", headers=owner)
    assert response.status_code == 503
    assert "private SQL" not in response.text + caplog.text
    assert "private answer" not in response.text + caplog.text
    assert history_rows(database) == saved
    assert stored_rows(database) == before

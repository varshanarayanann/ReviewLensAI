from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import QuestionExchange
from tests.conftest import USER_A_ID
from tests.test_ingestion_submission import source_targets as source_targets
from tests.test_target_workflow import database as database


def test_new_session_restores_only_active_targets_history_in_creation_order(
    client, database, source_targets, make_token, fake_llm
):
    owner, battery = source_targets[0]
    other_owner, _ = source_targets[1]
    service = client.post(
        "/api/targets",
        headers=owner,
        json={"name": "Service", "source_url": "https://google.com/maps/place/Service"},
    ).json()["id"]
    for target, review in (
        (battery, "Excellent battery life"),
        (service, "Slow customer service"),
    ):
        assert (
            client.post(
                f"/api/targets/{target}/ingestions",
                headers=owner,
                json={"csv_text": f"rating,review_text\n4,{review}"},
            ).status_code
            == 200
        )
    questions = [
        (battery, "Battery follow-up?", "Battery answer two", 2),
        (service, "How is customer service?", "Service answer", 1),
        (battery, "How long does the battery last?", "Battery answer one", 0),
    ]
    for target, question, answer, sequence in questions:
        fake_llm.respond_with(answer)
        assert (
            client.post(
                f"/api/targets/{target}/questions",
                headers=owner,
                json={"question": question},
            ).status_code
            == 200
        )
        with Session(database) as db:
            db.execute(
                update(QuestionExchange)
                .where(QuestionExchange.question == question)
                .values(
                    created_at=datetime(2026, 1, 1, tzinfo=UTC)
                    + timedelta(minutes=sequence)
                )
            )
            db.commit()

    token = make_token(sub=USER_A_ID, session_id=str(uuid4()))
    with TestClient(client.app) as restored:
        headers = {"Authorization": f"Bearer {token}"}
        for target, expected in (
            (battery, ["How long does the battery last?", "Battery follow-up?"]),
            (service, ["How is customer service?"]),
            (battery, ["How long does the battery last?", "Battery follow-up?"]),
        ):
            response = restored.get(f"/api/targets/{target}/questions", headers=headers)
            assert response.status_code == 200
            rows = response.json()
            assert [row["question"] for row in rows] == expected
            assert all(UUID(row["target_id"]) == UUID(target) for row in rows)
            assert [row["answer"] for row in rows] == (
                ["Battery answer one", "Battery answer two"]
                if target == battery
                else ["Service answer"]
            )
            assert (
                restored.get(
                    f"/api/targets/{target}/questions", headers=other_owner
                ).status_code
                == 404
            )
        page = restored.get(
            f"/api/targets/{battery}/questions?limit=1&offset=1", headers=headers
        ).json()
        assert page[0]["question"] == "Battery follow-up?"
    assert len(fake_llm.requests) == 3  # Restoring history never invokes the model.

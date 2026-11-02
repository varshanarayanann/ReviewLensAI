from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisTarget, Base
from tests.conftest import USER_A_ID
from tests.test_target_workflow import database as database  # Shared DB fixture.

USER_B_ID = "22222222-2222-4222-8222-222222222222"


def test_list_only_persisted_targets_owned_by_verified_user(
    client, make_token, database
):
    with database.begin() as connection:
        connection.execute(
            Base.metadata.tables["auth.users"].insert().values(id=UUID(USER_B_ID))
        )
    created = {}
    for subject in (USER_A_ID, USER_B_ID):
        headers = {"Authorization": f"Bearer {make_token(sub=subject)}"}
        ids = []
        for index in range(2):
            response = client.post(
                "/api/targets",
                headers=headers,
                json={
                    "name": f"Target {subject[:8]} {index}",
                    "source_url": f"https://google.com/maps/place/Business{index}",
                },
            )
            assert response.status_code == 201
            ids.append(UUID(response.json()["id"]))
        created[subject] = ids

    # Deliberate timestamps prove newest-first sorting independently of UUIDs.
    with Session(database) as db:
        for ids in created.values():
            for index, target_id in enumerate(ids):
                db.get(AnalysisTarget, target_id).created_at = datetime(
                    2026, 1, 1, tzinfo=UTC
                ) + timedelta(days=index)
        db.commit()

    for subject, spoofed in ((USER_A_ID, USER_B_ID), (USER_B_ID, USER_A_ID)):
        response = client.get(
            "/api/targets",
            headers={
                "Authorization": f"Bearer {make_token(sub=subject)}",
                "X-User-Id": spoofed,
            },
            params={"owner_id": spoofed, "userId": spoofed},
        )
        assert response.status_code == 200
        targets = response.json()
        assert [UUID(row["id"]) for row in targets] == list(reversed(created[subject]))
        assert all(row["platform"] == "google_maps" for row in targets)
        assert all(row["name"].startswith(f"Target {subject[:8]}") for row in targets)
        assert all(
            row["source_url"].startswith("https://google.com/maps/") for row in targets
        )
        assert all(
            set(row) == {"id", "name", "platform", "source_url", "created_at"}
            for row in targets
        )

    with Session(database) as db:
        assert len(db.scalars(select(AnalysisTarget)).all()) == 4


def test_user_without_targets_receives_empty_list(client, make_token, database):
    client.post(
        "/api/targets",
        headers={"Authorization": f"Bearer {make_token()}"},
        json={"name": "A only", "source_url": "https://google.com/maps/place/X"},
    )
    response = client.get(
        "/api/targets", headers={"Authorization": f"Bearer {make_token(sub=USER_B_ID)}"}
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("token", [None, "invalid-token"])
def test_target_list_requires_verified_auth(client, database, token):
    headers = {"X-User-Id": USER_A_ID}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    response = client.get("/api/targets", headers=headers)
    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}

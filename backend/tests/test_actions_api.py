from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models import ActionItem
from tests.conftest import USER_A_ID
from tests.test_ingestion_submission import source_targets as source_targets
from tests.test_ingestion_submission import stored_rows
from tests.test_target_workflow import database as database


def path(target, item=None):
    return f"/api/targets/{target}/actions" + (f"/{item}" if item else "")


def create(client, headers, target, **body):
    return client.post(
        path(target), headers=headers, json={"title": "Fix wait times", **body}
    )


def snapshot(database):
    with database.connect() as connection:
        return connection.execute(select(ActionItem).order_by(ActionItem.id)).all()


def test_create_list_update_reopen_and_delete_persist_across_requests(
    client, database, source_targets
):
    owner, target = source_targets[0]
    assert client.get(path(target), headers=owner).json() == []
    response = create(
        client,
        owner,
        target,
        title="  Reduce wait times  ",
        description="  Plan staffing ☕  ",
    )
    assert response.status_code == 201
    item = response.json()
    assert item["target_id"] == target and UUID(item["id"])
    assert (
        item["title"] == "Reduce wait times"
        and item["description"] == "Plan staffing ☕"
    )
    assert item["priority"] == "medium" and item["status"] == "open"
    assert datetime.fromisoformat(item["created_at"]).tzinfo is not None
    assert client.get(path(target), headers=owner).json() == [item]
    with Session(database) as db:
        assert db.get(ActionItem, UUID(item["id"])).title == item["title"]
    for status in ("in_progress", "resolved", "open", "done"):
        result = client.patch(
            path(target, item["id"]), headers=owner, json={"status": status}
        )
        assert result.status_code == 200
        changed = result.json()
        assert changed["status"] == ("done" if status == "resolved" else status)
        assert changed["created_at"] == item["created_at"]
        assert datetime.fromisoformat(changed["updated_at"]) >= datetime.fromisoformat(
            item["updated_at"]
        )
        assert client.get(path(target), headers=owner).json() == [changed]
    result = client.patch(
        path(target, item["id"]),
        headers=owner,
        json={"title": " Updated title ", "description": None, "priority": "high"},
    )
    assert result.status_code == 200
    assert result.json()["title"] == "Updated title"
    assert result.json()["description"] is None and result.json()["priority"] == "high"
    response = client.delete(path(target, item["id"]), headers=owner)
    assert response.status_code == 204 and response.content == b""
    assert client.get(path(target), headers=owner).json() == []
    assert client.delete(path(target, item["id"]), headers=owner).status_code == 404


def test_owned_targets_and_accounts_are_isolated_and_list_order_is_stable(
    client, database, source_targets
):
    owner, target = source_targets[0]
    other, other_target = source_targets[1]
    first = create(client, owner, target, title="First", priority="low").json()
    second = create(client, owner, target, title="Second").json()
    theirs = create(client, other, other_target, title="Private other account").json()
    now = datetime.now(UTC)
    with Session(database) as db:
        db.execute(
            update(ActionItem)
            .where(ActionItem.id == UUID(first["id"]))
            .values(created_at=now)
        )
        db.execute(
            update(ActionItem)
            .where(ActionItem.id == UUID(second["id"]))
            .values(created_at=now - timedelta(days=1))
        )
        db.commit()
    assert [row["id"] for row in client.get(path(target), headers=owner).json()] == [
        second["id"],
        first["id"],
    ]
    assert client.get(path(other_target), headers=other).json() == [theirs]
    another = client.post(
        "/api/targets",
        headers=owner,
        json={
            "name": "Same owner, another target",
            "source_url": "https://google.com/maps/place/X",
        },
    ).json()["id"]
    before = snapshot(database)
    for wrong_target, headers in (
        (target, other),
        (other_target, owner),
        (another, owner),
        (str(uuid4()), owner),
    ):
        for method in ("PATCH", "DELETE"):
            response = client.request(
                method,
                path(wrong_target, first["id"]),
                headers=headers,
                json={"title": "Hacked"} if method == "PATCH" else None,
            )
            assert response.status_code == 404
    for method in ("GET", "POST"):
        response = client.request(
            method,
            path(target),
            headers={**other, "X-Owner-Id": USER_A_ID},
            params={"owner_id": USER_A_ID},
            json={"title": "Hacked"} if method == "POST" else None,
        )
        assert response.status_code == 404
    assert (
        client.patch(
            path(target, uuid4()), headers=owner, json={"title": "Missing"}
        ).status_code
        == 404
    )
    assert snapshot(database) == before


@pytest.mark.parametrize(
    "method,suffix,body",
    [
        ("GET", "", None),
        ("POST", "", {"title": "Task"}),
        ("PATCH", "/item", {"status": "done"}),
        ("DELETE", "/item", None),
    ],
)
def test_actions_require_authentication(client, method, suffix, body):
    suffix = f"/{uuid4()}" if suffix else ""
    assert client.request(method, path(uuid4()) + suffix, json=body).status_code == 401


@pytest.mark.parametrize(
    "body",
    [
        {"title": ""},
        {"title": " \t "},
        {"title": "x" * 201},
        {"title": None},
        {"priority": "urgent"},
        {"priority": None},
        {"description": "x" * 10001},
        {"owner_id": USER_A_ID},
        {"target_id": str(uuid4())},
        {"status": "done"},
    ],
)
def test_invalid_create_cannot_write(client, database, source_targets, body):
    owner, target = source_targets[0]
    assert create(client, owner, target, **body).status_code == 422
    assert snapshot(database) == []


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"title": " "},
        {"title": None},
        {"priority": "urgent"},
        {"priority": None},
        {"status": "closed"},
        {"status": None},
        {"description": "x" * 10001},
        {"id": str(uuid4())},
        {"target_id": str(uuid4())},
        {"owner_id": USER_A_ID},
    ],
)
def test_invalid_update_preserves_the_original_item(
    client, database, source_targets, body
):
    owner, target = source_targets[0]
    item = create(client, owner, target).json()
    before = snapshot(database)
    assert (
        client.patch(path(target, item["id"]), headers=owner, json=body).status_code
        == 422
    )
    assert snapshot(database) == before


def test_status_filter_uses_canonical_values_and_resolved_alias(
    client, database, source_targets
):
    owner, target = source_targets[0]
    item = create(client, owner, target).json()
    client.patch(path(target, item["id"]), headers=owner, json={"status": "resolved"})
    for status in ("done", "resolved"):
        response = client.get(path(target), headers=owner, params={"status": status})
        assert response.status_code == 200 and response.json()[0]["id"] == item["id"]
    assert (
        client.get(path(target), headers=owner, params={"status": "open"}).json() == []
    )
    assert (
        client.get(path(target), headers=owner, params={"status": "bogus"}).status_code
        == 422
    )


@pytest.mark.parametrize("method", ["POST", "PATCH", "DELETE"])
@pytest.mark.parametrize("rollback_fails", [False, True])
def test_failed_writes_rollback_and_redact_diagnostics(
    client, database, source_targets, monkeypatch, caplog, method, rollback_fails
):
    owner, target = source_targets[0]
    item = create(client, owner, target).json()
    before = snapshot(database)

    def fail(*args, **kwargs):
        raise OperationalError(
            "secret SQL", {}, RuntimeError("private task description")
        )

    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", fail)
        if rollback_fails:
            patch.setattr(Session, "rollback", fail)
        response = client.request(
            method,
            path(target, None if method == "POST" else item["id"]),
            headers=owner,
            json={"title": "New title"} if method != "DELETE" else None,
        )
    assert response.status_code == 503
    assert "secret SQL" not in response.text + caplog.text
    assert "private task description" not in response.text + caplog.text
    assert snapshot(database) == before


def test_read_failure_is_safely_mapped(client, database, source_targets, monkeypatch):
    owner, target = source_targets[0]

    def fail(*args, **kwargs):
        raise OperationalError("private query", {}, RuntimeError())

    monkeypatch.setattr(Session, "scalars", fail)
    response = client.get(path(target), headers=owner)
    assert response.status_code == 503 and "private query" not in response.text


def test_delete_cascades_future_evidence_links_without_removing_reviews(
    client, database, source_targets
):
    owner, target = source_targets[0]
    item = create(client, owner, target).json()
    client.post(
        f"/api/targets/{target}/ingestions",
        headers=owner,
        json={"csv_text": "rating,review_text\n5,Supporting review"},
    )
    review = client.get(f"/api/targets/{target}/reviews", headers=owner).json()[0]
    # S3-025 is not on main yet. Exercise its agreed FK contract in disposable
    # test storage only; production must not invent a competing evidence model.
    with database.begin() as connection:
        if database.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            key_type = "CHAR(32)"
            action_id, review_id = UUID(item["id"]).hex, UUID(review["id"]).hex
        else:
            key_type = "UUID"
            action_id, review_id = item["id"], review["id"]
        connection.exec_driver_sql(
            f"CREATE TABLE action_item_reviews (action_item_id {key_type} "
            "REFERENCES action_items(id) ON DELETE CASCADE, "
            f"review_id {key_type} REFERENCES reviews(id), "
            "PRIMARY KEY(action_item_id, review_id))"
        )
        connection.execute(
            text("INSERT INTO action_item_reviews VALUES (:action, :review)"),
            {"action": action_id, "review": review_id},
        )
    before = stored_rows(database)
    response = client.delete(path(target, item["id"]), headers=owner)
    assert response.status_code == 204
    assert stored_rows(database) == before
    with database.connect() as connection:
        assert connection.scalar(text("SELECT COUNT(*) FROM action_item_reviews")) == 0

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ActionItem
from tests.test_ingestion_submission import source_targets as source_targets
from tests.test_target_workflow import database as database


def seed_action_item(
    database,
    target_id: str,
    title: str,
    *,
    description: str | None = "Follow up with the manager.",
    priority: str = "high",
    status: str = "in_progress",
) -> str:
    item_id = uuid4()
    with Session(database) as db:
        db.add(
            ActionItem(
                id=item_id,
                target_id=UUID(target_id),
                title=title,
                description=description,
                priority=priority,
                status=status,
            )
        )
        db.commit()
    return str(item_id)


def action_items_for(database, target_id: str) -> list[ActionItem]:
    with Session(database) as db:
        return list(
            db.scalars(
                select(ActionItem)
                .where(ActionItem.target_id == UUID(target_id))
                .order_by(ActionItem.created_at, ActionItem.id)
            ).all()
        )


def test_rename_leaves_action_items_unchanged(client, database, source_targets):
    owner, target = source_targets[0]
    item_id = seed_action_item(database, target, "Fix wait times")
    before = action_items_for(database, target)
    assert len(before) == 1

    response = client.patch(
        f"/api/targets/{target}", headers=owner, json={"name": "Renamed Cafe"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed Cafe"

    after = action_items_for(database, target)
    assert len(after) == 1
    assert str(after[0].id) == item_id
    assert after[0].title == "Fix wait times"
    assert after[0].description == before[0].description
    assert after[0].priority == before[0].priority
    assert after[0].status == before[0].status


def test_reopening_analysis_preserves_saved_action_items(
    client, database, source_targets
):
    owner, target = source_targets[0]
    item_id = seed_action_item(database, target, "Improve seating")
    assert client.get(f"/api/targets/{target}", headers=owner).status_code == 200

    # Simulate leaving and returning: list targets, then reopen the same analysis.
    listed = client.get("/api/targets", headers=owner)
    assert listed.status_code == 200
    assert any(row["id"] == target for row in listed.json())

    reopened = client.get(f"/api/targets/{target}", headers=owner)
    assert reopened.status_code == 200
    assert reopened.json()["id"] == target

    items = action_items_for(database, target)
    assert len(items) == 1
    assert str(items[0].id) == item_id
    assert items[0].title == "Improve seating"


def test_save_as_starts_with_empty_action_tracker_and_keeps_original(
    client, database, source_targets
):
    owner, target = source_targets[0]
    item_id = seed_action_item(
        database,
        target,
        "Original tracker item",
        description="Stay on the source analysis only.",
        priority="low",
        status="open",
    )
    original_before = action_items_for(database, target)

    response = client.post(
        f"/api/targets/{target}/copies",
        headers=owner,
        json={"name": "Cafe copy"},
    )
    assert response.status_code == 201
    copy_id = response.json()["id"]
    assert copy_id != target

    assert action_items_for(database, copy_id) == []

    original_after = action_items_for(database, target)
    assert len(original_after) == 1
    assert str(original_after[0].id) == item_id
    assert original_after[0].title == original_before[0].title
    assert original_after[0].description == original_before[0].description
    assert original_after[0].priority == original_before[0].priority
    assert original_after[0].status == original_before[0].status


def test_delete_removes_action_items_for_target_only(client, database, source_targets):
    owner, target = source_targets[0]
    other_owner, other_target = source_targets[1]
    deleted_item = seed_action_item(database, target, "Remove with analysis")
    kept_item = seed_action_item(database, other_target, "Keep on other analysis")

    response = client.delete(f"/api/targets/{target}", headers=owner)
    assert response.status_code == 204

    assert action_items_for(database, target) == []
    with Session(database) as db:
        assert db.get(ActionItem, UUID(deleted_item)) is None
        kept = db.get(ActionItem, UUID(kept_item))
        assert kept is not None
        assert str(kept.target_id) == other_target
        assert kept.title == "Keep on other analysis"

    remaining = action_items_for(database, other_target)
    assert len(remaining) == 1
    assert str(remaining[0].id) == kept_item
    assert (
        client.get(f"/api/targets/{other_target}", headers=other_owner).status_code
        == 200
    )


def test_other_user_cannot_delete_analysis_or_its_action_items(
    client, database, source_targets
):
    owner, target = source_targets[0]
    other_owner, _ = source_targets[1]
    item_id = seed_action_item(database, target, "Owner-only item")
    before = action_items_for(database, target)

    denied = client.delete(f"/api/targets/{target}", headers=other_owner)
    assert denied.status_code == 404

    after = action_items_for(database, target)
    assert len(after) == 1
    assert str(after[0].id) == item_id
    assert after[0].title == before[0].title
    assert client.get(f"/api/targets/{target}", headers=owner).status_code == 200

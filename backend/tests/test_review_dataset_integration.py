"""Integration tests across CSV ingestion, persistence, ownership, and retrieval."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Base
from app.models.ingestion import IngestionRun, Review
from tests.conftest import USER_A_ID
from tests.test_target_workflow import USER_B_ID
from tests.test_target_workflow import database as database  # Shared DB fixture.

BATTERY_CSV = (
    "rating,review_text\n"
    '5,"Battery life lasts two days, amazing"\n'
    "4,Battery life is solid for travel\n"
    "2,  Battery life dropped after a month  \n"
)
BATTERY_DATASET = [
    (2, "Battery life dropped after a month"),
    (4, "Battery life is solid for travel"),
    (5, "Battery life lasts two days, amazing"),
]
SERVICE_CSV = (
    "rating,review_text\n"
    "1,Customer service never called back\n"
    "3,Customer service was polite but slow\n"
)
SERVICE_DATASET = [
    (1, "Customer service never called back"),
    (3, "Customer service was polite but slow"),
]


@pytest.fixture
def as_user(make_token, database):
    with database.begin() as connection:
        connection.execute(
            Base.metadata.tables["auth.users"].insert().values(id=UUID(USER_B_ID))
        )

    def headers(subject: str = USER_A_ID) -> dict[str, str]:
        return {"Authorization": f"Bearer {make_token(sub=subject)}"}

    return headers


def create_target(client, headers, name):
    response = client.post(
        "/api/targets",
        headers=headers,
        json={"name": name, "source_url": "https://google.com/maps/place/X"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def ingest(client, headers, target_id, csv_text):
    response = client.post(
        f"/api/targets/{target_id}/ingestions",
        headers=headers,
        json={"csv_text": csv_text},
    )
    assert response.status_code == 200
    return response.json()


def review_rows(client, headers, target_id):
    response = client.get(
        f"/api/targets/{target_id}/reviews", headers=headers, params={"limit": 100}
    )
    assert response.status_code == 200
    return response.json()


def dataset(client, headers, target_id):
    return sorted(
        (row["rating"], row["review_text"])
        for row in review_rows(client, headers, target_id)
    )


def latest(client, headers, target_id):
    response = client.get(
        f"/api/targets/{target_id}/ingestions/latest", headers=headers
    )
    assert response.status_code == 200
    return response.json()


def test_uploaded_csv_is_retrievable_as_the_persisted_dataset(
    client, database, as_user
):
    owner = as_user()
    target_id = create_target(client, owner, "Phone store")

    result = ingest(client, owner, target_id, BATTERY_CSV)

    assert result["state"] == "succeeded"
    assert result["persisted_count"] == len(BATTERY_DATASET)
    assert dataset(client, owner, target_id) == BATTERY_DATASET
    rows = review_rows(client, owner, target_id)
    assert {row["run_id"] for row in rows} == {result["run_id"]}
    assert {row["target_id"] for row in rows} == {target_id}
    assert latest(client, owner, target_id) == result
    with Session(database) as db:
        stored = db.scalar(
            select(func.count())
            .select_from(Review)
            .where(Review.run_id == UUID(result["run_id"]))
        )
    assert stored == result["persisted_count"]


def test_switching_targets_returns_only_the_selected_dataset(client, as_user):
    owner = as_user()
    battery = create_target(client, owner, "Phone store")
    service = create_target(client, owner, "Call center")
    battery_result = ingest(client, owner, battery, BATTERY_CSV)
    service_result = ingest(client, owner, service, SERVICE_CSV)

    for target_id, expected, result in (
        (battery, BATTERY_DATASET, battery_result),
        (service, SERVICE_DATASET, service_result),
        (battery, BATTERY_DATASET, battery_result),
    ):
        assert dataset(client, owner, target_id) == expected
        assert latest(client, owner, target_id) == result

    battery_ids = {row["id"] for row in review_rows(client, owner, battery)}
    service_ids = {row["id"] for row in review_rows(client, owner, service)}
    assert battery_ids.isdisjoint(service_ids)

    ingest(client, owner, service, "rating,review_text\n2,Customer service hung up")
    assert dataset(client, owner, battery) == BATTERY_DATASET
    assert latest(client, owner, battery) == battery_result


def test_rejected_upload_rows_never_enter_the_dataset(client, database, as_user):
    owner = as_user()
    target_id = create_target(client, owner, "Phone store")
    ingest(client, owner, target_id, BATTERY_CSV)

    rejected = ingest(
        client,
        owner,
        target_id,
        "rating,review_text\n5,Looks valid but shares a file\nnot-a-number,Broken",
    )

    assert rejected["state"] == "failed"
    assert rejected["persisted_count"] == 0
    assert latest(client, owner, target_id) == rejected
    assert dataset(client, owner, target_id) == BATTERY_DATASET
    with Session(database) as db:
        run = db.get(IngestionRun, UUID(rejected["run_id"]))
        leaked = db.scalars(select(Review).where(Review.run_id == run.id)).all()
    assert run.state == "failed"
    assert leaked == []


@pytest.mark.parametrize("suffix", ["", "/reviews", "/ingestions/latest"])
def test_selecting_another_users_target_is_denied_before_data_is_read(
    client, as_user, suffix
):
    user_a, user_b = as_user(USER_A_ID), as_user(USER_B_ID)
    private = create_target(client, user_a, "Phone store")
    ingest(client, user_a, private, BATTERY_CSV)
    own = create_target(client, user_b, "Call center")
    ingest(client, user_b, own, SERVICE_CSV)

    denied = client.get(f"/api/targets/{private}{suffix}", headers=user_b)
    missing = client.get(f"/api/targets/{uuid4()}{suffix}", headers=user_b)

    assert denied.status_code == missing.status_code == 404
    assert denied.json() == missing.json()
    assert "Battery" not in denied.text and "Phone store" not in denied.text
    assert dataset(client, user_b, own) == SERVICE_DATASET
    assert dataset(client, user_a, private) == BATTERY_DATASET

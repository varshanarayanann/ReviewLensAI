from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ingestion import IngestionRun, Review
from tests.test_target_workflow import database as database  # Shared DB fixture.


def test_workspace_contract_and_cross_user_denial(client, make_token, database):
    owner = {"Authorization": f"Bearer {make_token()}"}
    other = {"Authorization": f"Bearer {make_token(sub=str(uuid4()))}"}
    created = client.post(
        "/api/targets",
        headers=owner,
        json={
            "name": "Workspace business",
            "source_url": "https://google.com/maps/place/X",
        },
    )
    assert created.status_code == 201
    target_id = created.json()["id"]
    path = f"/api/targets/{target_id}"
    response = client.get(path, headers=owner)
    assert response.status_code == 200
    assert response.json() == {
        "id": target_id,
        "name": "Workspace business",
        "platform": "google_maps",
        "source_url": "https://google.com/maps/place/X",
    }
    assert client.get(path + "/ingestions/latest", headers=owner).json() is None
    imported = client.post(
        path + "/ingestions",
        headers=owner,
        json={"csv_text": "rating,review_text\n5,Great"},
    )
    assert imported.status_code == 200
    assert imported.json()["state"] == "succeeded"
    assert (
        client.get(path + "/ingestions/latest", headers=owner).json() == imported.json()
    )
    for suffix in ("", "/ingestions/latest"):
        denied = client.get(path + suffix, headers=other)
        missing = client.get(f"/api/targets/{uuid4()}{suffix}", headers=other)
        assert denied.status_code == missing.status_code == 404
        assert denied.json() == missing.json()
    assert (
        client.post(
            path + "/ingestions",
            headers=other,
            json={"csv_text": "rating,review_text\n1,Denied"},
        ).status_code
        == 404
    )
    with Session(database) as db:
        reviews = db.scalars(select(Review)).all()
        assert len(reviews) == 1 and reviews[0].target_id == UUID(target_id)
        assert len(db.scalars(select(IngestionRun)).all()) == 1

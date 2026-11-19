from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.conftest import USER_A_ID
from tests.test_ingestion_submission import source_targets as source_targets
from tests.test_target_workflow import database as database


@pytest.mark.parametrize("failed_latest", [False, True])
def test_new_authenticated_session_reopens_persisted_workspace(
    client, database, source_targets, make_token, failed_latest
):
    owner, target = source_targets[0]
    csv = "rating,review_text\n5,Saved walking paths\n3,Busy parking"
    result = client.post(
        f"/api/targets/{target}/ingestions", headers=owner, json={"csv_text": csv}
    )
    assert result.status_code == 200
    original_reviews = client.get(
        f"/api/targets/{target}/reviews", headers=owner
    ).json()
    if failed_latest:
        result = client.post(
            f"/api/targets/{target}/ingestions",
            headers=owner,
            json={"csv_text": "rating,review_text\nnot-a-rating,Rejected"},
        )
        assert result.json()["state"] == "failed"

    # Restore through a new HTTP client/token, with no browser or ORM cache.
    new_session = {
        "Authorization": f"Bearer {make_token(sub=USER_A_ID, session_id=str(uuid4()))}"
    }
    with TestClient(client.app) as reopened:
        path = f"/api/targets/{target}"
        target_data = reopened.get(path, headers=new_session).json()
        assert target_data["name"] == "Source target"
        assert target_data["platform"] == "google_maps"
        assert target_data["source_url"] == "https://google.com/maps/place/X"
        assert target in [
            row["id"]
            for row in reopened.get("/api/targets", headers=new_session).json()
        ]
        assert (
            reopened.get(path + "/ingestions/latest", headers=new_session).json()
            == result.json()
        )
        assert (
            reopened.get(path + "/reviews", headers=new_session).json()
            == original_reviews
        )
        assert reopened.get(path + "/reviews/summary", headers=new_session).json() == {
            "target_id": target,
            "review_count": 2,
            "average_rating": 4,
        }
        other, _ = source_targets[1]
        for suffix in ("", "/reviews", "/reviews/summary", "/ingestions/latest"):
            assert reopened.get(path + suffix, headers=other).status_code == 404
            assert reopened.get(path + suffix).status_code == 401

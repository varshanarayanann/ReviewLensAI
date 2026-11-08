from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Base
from app.models.ingestion import Review
from tests.conftest import USER_A_ID
from tests.test_target_workflow import USER_B_ID
from tests.test_target_workflow import database as database  # Shared DB fixture.


def headers(make_token, subject=USER_A_ID):
    return {"Authorization": "Bearer " + make_token(sub=subject)}


def create_target(client, auth, name):
    response = client.post(
        "/api/targets",
        headers=auth,
        json={"name": name, "source_url": "https://google.com/maps/place/X"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def ingest(client, auth, target_id, rows):
    response = client.post(
        f"/api/targets/{target_id}/ingestions",
        headers=auth,
        json={"csv_text": "rating,review_text\n" + rows},
    )
    assert response.status_code == 200
    return response.json()


def summary(client, auth, target_id):
    return client.get(f"/api/targets/{target_id}/reviews/summary", headers=auth)


def test_summary_tracks_added_and_deleted_persisted_reviews(
    client, make_token, database
):
    auth = headers(make_token)
    target_id = create_target(client, auth, "Target")
    ingest(client, auth, target_id, "2,Review one")

    first = summary(client, auth, target_id)
    assert first.status_code == 200
    assert first.json() == {
        "target_id": target_id,
        "review_count": 1,
        "average_rating": 2.0,
    }

    ingest(client, auth, target_id, "4,Review two")
    added = summary(client, auth, target_id)
    assert added.json()["review_count"] == 2
    assert added.json()["average_rating"] == 3.0

    with Session(database) as db:
        review = db.scalar(
            select(Review).where(
                Review.target_id == UUID(target_id), Review.rating == 2
            )
        )
        db.delete(review)
        db.commit()

    deleted = summary(client, auth, target_id)
    assert deleted.json()["review_count"] == 1
    assert deleted.json()["average_rating"] == 4.0


def test_target_summaries_are_independent(client, make_token, database):
    auth = headers(make_token)
    target_a = create_target(client, auth, "Target A")
    target_b = create_target(client, auth, "Target B")
    ingest(client, auth, target_a, "5,Great\n3,Good")
    ingest(client, auth, target_b, "1,Bad")

    summary_a = summary(client, auth, target_a)
    summary_b = summary(client, auth, target_b)

    assert summary_a.json() == {
        "target_id": target_a,
        "review_count": 2,
        "average_rating": 4.0,
    }
    assert summary_b.json() == {
        "target_id": target_b,
        "review_count": 1,
        "average_rating": 1.0,
    }

    ingest(client, auth, target_b, "5,Another review")

    assert summary(client, auth, target_a).json() == {
        "target_id": target_a,
        "review_count": 2,
        "average_rating": 4.0,
    }
    assert summary(client, auth, target_b).json() == {
        "target_id": target_b,
        "review_count": 2,
        "average_rating": 3.0,
    }


def test_summary_counts_reviews_beyond_the_list_page_size(client, make_token, database):
    auth = headers(make_token)
    target_id = create_target(client, auth, "Large target")
    reviews = "\n".join(f"{index % 5 + 1},Review {index}" for index in range(125))
    ingest(client, auth, target_id, reviews)

    listed = client.get(f"/api/targets/{target_id}/reviews", headers=auth)
    summarized = summary(client, auth, target_id)

    assert listed.status_code == summarized.status_code == 200
    assert len(listed.json()) == 50
    assert summarized.json()["review_count"] == 125
    assert summarized.json()["average_rating"] == 3.0


def test_other_users_summary_matches_missing_target_response(
    client, make_token, database
):
    with database.begin() as connection:
        connection.execute(
            Base.metadata.tables["auth.users"].insert().values(id=UUID(USER_B_ID))
        )
    user_a = headers(make_token)
    user_b = headers(make_token, USER_B_ID)
    private_target = create_target(client, user_a, "Private")
    ingest(client, user_a, private_target, "5,Private review")

    denied = summary(client, user_b, private_target)
    missing = summary(client, user_b, str(uuid4()))

    assert denied.status_code == missing.status_code == 404
    assert denied.json() == missing.json() == {"detail": "Analysis target not found."}


def test_empty_target_summary_has_null_average(client, make_token, database):
    auth = headers(make_token)
    target_id = create_target(client, auth, "Empty")

    response = summary(client, auth, target_id)

    assert response.status_code == 200
    assert response.json() == {
        "target_id": target_id,
        "review_count": 0,
        "average_rating": None,
    }


def test_failed_ingestion_does_not_change_existing_summary(
    client, make_token, database
):
    auth = headers(make_token)
    target_id = create_target(client, auth, "Target")
    ingest(client, auth, target_id, "5,Great\n3,Good")
    before = summary(client, auth, target_id).json()

    failed = ingest(client, auth, target_id, "4,Would be valid\ninvalid,Broken")
    after = summary(client, auth, target_id)

    assert failed["state"] == "failed"
    assert after.status_code == 200
    assert (
        after.json()
        == before
        == {
            "target_id": target_id,
            "review_count": 2,
            "average_rating": 4.0,
        }
    )

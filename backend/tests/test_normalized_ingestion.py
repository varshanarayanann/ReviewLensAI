from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.ingestion import IngestionRun, Review
from app.reviews.csv_source import parse_csv_reviews
from app.reviews.normalization import normalize_reviews
from tests.test_target_workflow import database as database  # Shared DB fixture.

FIXTURE = Path(__file__).parent / "fixtures" / "google_maps_export.csv"


def source_target(client, make_token):
    headers = {"Authorization": f"Bearer {make_token()}"}
    target = client.post(
        "/api/targets",
        headers=headers,
        json={
            "name": "Normalized target",
            "source_url": "https://google.com/maps/place/X",
        },
    )
    assert target.status_code == 201
    target_id = target.json()["id"]
    return headers, target_id, f"/api/targets/{target_id}/ingestions"


def test_source_adapter_to_canonical_review_to_persisted_metadata(
    client, make_token, database
):
    source = FIXTURE.read_text(encoding="utf-8")
    normalized = normalize_reviews(parse_csv_reviews(source))
    assert not normalized.rejected and len(normalized.reviews) == 3
    headers, target, path = source_target(client, make_token)
    response = client.post(path, headers=headers, json={"csv_text": source})
    assert response.status_code == 200
    assert response.json()["state"] == "succeeded"
    assert response.json()["persisted_count"] == 3
    with Session(database) as db:
        stored = db.scalars(select(Review)).all()
        by_source = {
            review.source_metadata["source_review_id"]: review for review in stored
        }
        for canonical in normalized.reviews:
            review = by_source[canonical.source_metadata["source_review_id"]]
            assert (review.review_text, review.rating) == (
                canonical.review_text,
                canonical.rating,
            )
            assert review.source_metadata == canonical.source_metadata
            assert review.target_id == UUID(target)


def test_absent_metadata_and_untrusted_association_fields(client, make_token, database):
    headers, target, path = source_target(client, make_token)
    plain = client.post(
        path, headers=headers, json={"csv_text": "rating,review_text\n4.0, Plain "}
    )
    assert plain.json()["state"] == "succeeded"
    attack = client.post(
        path,
        headers=headers,
        json={
            "csv_text": "rating,review_text,owner_id,target_id,run_id\n"
            "5,Other,forged,forged,forged"
        },
    )
    assert attack.json()["state"] == "succeeded"
    with Session(database) as db:
        stored = {review.review_text: review for review in db.scalars(select(Review))}
        assert stored["Plain"].source_metadata == {}
        assert stored["Plain"].rating == 4
        review = stored["Other"]
        assert review.source_metadata == {
            "owner_id": "forged",
            "target_id": "forged",
            "run_id": "forged",
        }
        assert review.target_id == UUID(target)
        assert str(review.run_id) == attack.json()["run_id"]


@pytest.mark.parametrize(
    "bad_record", ["4,", ",Missing rating", "4.5,Fractional", "bad,Not numeric"]
)
def test_mixed_import_fails_atomically_and_preserves_previous_reviews(
    client, make_token, database, bad_record
):
    headers, _, path = source_target(client, make_token)
    client.post(
        path,
        headers=headers,
        json={"csv_text": "rating,review_text\n5,Previously stored"},
    )
    mixed = client.post(
        path,
        headers=headers,
        json={"csv_text": "rating,review_text\n5,Usable candidate\n" + bad_record},
    )
    assert mixed.status_code == 200
    assert mixed.json()["state"] == "failed" and mixed.json()["persisted_count"] == 0
    assert client.get(path + "/latest", headers=headers).json() == mixed.json()
    with Session(database) as db:
        assert [review.review_text for review in db.scalars(select(Review))] == [
            "Previously stored"
        ]
        assert len(db.scalars(select(IngestionRun)).all()) == 2


def test_metadata_migration_backfills_existing_rows_and_has_object_constraint(
    client, make_token, database
):
    headers, _, path = source_target(client, make_token)
    result = client.post(
        path,
        headers=headers,
        json={"csv_text": "rating,review_text\n5,Existing review"},
    )
    assert result.json()["state"] == "succeeded"
    if database.dialect.name == "postgresql":
        # Emulate the existing schema/data immediately before migration 0003 in
        # this isolated test database, then apply the actual committed SQL.
        with database.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE reviews DROP COLUMN source_metadata"
            )
            connection.exec_driver_sql(
                (
                    Path(__file__).parents[1]
                    / "migrations"
                    / "0003_add_review_source_metadata.sql"
                ).read_text()
            )
        with pytest.raises(IntegrityError), database.begin() as connection:
            connection.execute(text("UPDATE reviews SET source_metadata = '[]'::jsonb"))
    with Session(database) as db:
        review = db.scalar(select(Review))
        assert review.source_metadata == {} and review.review_text == "Existing review"

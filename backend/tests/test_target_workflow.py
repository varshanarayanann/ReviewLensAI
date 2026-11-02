import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Column, Table, Uuid, create_engine, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import get_db, to_sqlalchemy_url
from app.models import AnalysisTarget, Base
from app.models.ingestion import IngestionRun, Review
from tests.conftest import USER_A_ID

USER_B_ID = "22222222-2222-4222-8222-222222222222"


@pytest.fixture(params=["sqlite", "postgres"])
def database(client, request):
    admin = None
    users = Table(
        "users", Base.metadata, Column("id", Uuid, primary_key=True), schema="auth"
    )
    engine = None
    database_name = "reviewlens_test_" + uuid4().hex
    try:
        if request.param == "postgres":
            url = os.environ.get("TEST_POSTGRES_URL")
            if not url:
                pytest.skip("Set TEST_POSTGRES_URL to a disposable PostgreSQL server")
            admin = create_engine(to_sqlalchemy_url(url), isolation_level="AUTOCOMMIT")
            with admin.connect() as connection:
                connection.exec_driver_sql(f'CREATE DATABASE "{database_name}"')
            engine = create_engine(admin.url.set(database=database_name))
            with engine.begin() as connection:
                # Supabase supplies auth.users; reproduce its referenced key only.
                connection.exec_driver_sql("CREATE SCHEMA auth")
                connection.exec_driver_sql(
                    "CREATE TABLE auth.users (id UUID PRIMARY KEY)"
                )
                for migration in sorted(
                    (Path(__file__).parents[1] / "migrations").glob("*.sql")
                ):
                    connection.exec_driver_sql(migration.read_text())
                connection.execute(users.insert().values(id=UUID(USER_A_ID)))
        else:
            engine = create_engine(
                "sqlite://",
                poolclass=StaticPool,
                connect_args={"check_same_thread": False},
            )
            with engine.connect() as connection:
                connection.exec_driver_sql("ATTACH DATABASE ':memory:' AS auth")
                Base.metadata.create_all(connection)
                connection.execute(users.insert().values(id=UUID(USER_A_ID)))
                connection.commit()

        def session():
            with Session(engine) as db:
                yield db

        client.app.dependency_overrides[get_db] = session
        yield engine
    finally:
        client.app.dependency_overrides.pop(get_db, None)
        if engine is not None:
            engine.dispose()
        if admin is not None:
            with admin.connect() as connection:
                connection.exec_driver_sql(f'DROP DATABASE IF EXISTS "{database_name}"')
            admin.dispose()
        Base.metadata.remove(users)


def test_created_records_belong_to_verified_subject(client, make_token, database):
    with database.begin() as connection:
        connection.execute(
            Base.metadata.tables["auth.users"].insert().values(id=UUID(USER_B_ID))
        )

    targets = {}
    for subject, spoofed in ((USER_A_ID, USER_B_ID), (USER_B_ID, USER_A_ID)):
        headers = {
            "Authorization": f"Bearer {make_token(sub=subject)}",
            "X-User-Id": spoofed,
            "X-Owner-Id": spoofed,
        }
        response = client.post(
            "/api/targets",
            params={"userId": spoofed, "owner_id": spoofed},
            headers=headers,
            json={"name": "Same name", "source_url": "https://google.com/maps/place/X"},
        )
        assert response.status_code == 201
        target_id = UUID(response.json()["id"])
        targets[subject] = target_id
        imported = client.post(
            f"/api/targets/{target_id}/ingestions",
            headers=headers,
            json={"csv_text": "rating,review_text\n5,Great"},
        )
        assert imported.status_code == 200
        assert imported.json()["state"] == "succeeded"

    # Read through a fresh session to prove ownership and associations persisted.
    with Session(database) as db:
        assert len(db.scalars(select(AnalysisTarget)).all()) == 2
        for subject, target_id in targets.items():
            assert db.get(AnalysisTarget, target_id).owner_id == UUID(subject)
            run = db.scalar(
                select(IngestionRun).where(IngestionRun.target_id == target_id)
            )
            review = db.scalar(select(Review).where(Review.target_id == target_id))
            assert run is not None and review is not None
            assert review.run_id == run.id
            assert review.target_id == run.target_id == target_id

    for subject, other in ((USER_A_ID, USER_B_ID), (USER_B_ID, USER_A_ID)):
        headers = {"Authorization": f"Bearer {make_token(sub=subject)}"}
        path = f"/api/targets/{targets[other]}"
        assert client.get(path, headers=headers).status_code == 404
        assert (
            client.post(
                path + "/ingestions",
                headers=headers,
                json={"csv_text": "rating,review_text\n5,Denied"},
            ).status_code
            == 404
        )
    with Session(database) as db:
        assert len(db.scalars(select(IngestionRun)).all()) == 2
        assert len(db.scalars(select(Review)).all()) == 2


@pytest.mark.parametrize("token", [None, "invalid-token"])
def test_unverified_identity_cannot_create_records(client, database, token):
    headers = {"X-User-Id": USER_A_ID}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    response = client.post(
        "/api/targets",
        headers=headers,
        json={"name": "Denied", "source_url": "https://google.com/maps/place/X"},
    )
    assert response.status_code == 401
    with Session(database) as db:
        assert not db.scalars(select(AnalysisTarget)).all()


@pytest.mark.parametrize("field", ["owner_id", "ownerId", "user_id", "userId"])
def test_client_ownership_fields_cannot_create_target(
    client, make_token, database, field
):
    response = client.post(
        "/api/targets",
        headers={"Authorization": f"Bearer {make_token()}"},
        json={
            "name": "Spoofed",
            "source_url": "https://google.com/maps/place/X",
            field: USER_B_ID,
        },
    )
    assert response.status_code == 422
    with Session(database) as db:
        assert not db.scalars(select(AnalysisTarget)).all()


@pytest.mark.parametrize("field", ["owner_id", "userId", "target_id", "run_id"])
def test_import_rejects_client_ownership_and_association_fields(
    client, make_token, database, field
):
    headers = {"Authorization": f"Bearer {make_token()}"}
    target_id = client.post(
        "/api/targets",
        headers=headers,
        json={"name": "Owned", "source_url": "https://google.com/maps/place/X"},
    ).json()["id"]
    response = client.post(
        f"/api/targets/{target_id}/ingestions",
        headers=headers,
        json={"csv_text": "rating,review_text\n5,Great", field: USER_B_ID},
    )
    assert response.status_code == 422
    with Session(database) as db:
        assert db.get(AnalysisTarget, UUID(target_id)).owner_id == UUID(USER_A_ID)
        assert not db.scalars(select(IngestionRun)).all()
        assert not db.scalars(select(Review)).all()


def test_validation_ingestion_and_failure_preserves_reviews(
    client, make_token, database
):
    headers = {"Authorization": f"Bearer {make_token()}"}
    assert (
        client.post("/api/targets", headers=headers, json={"name": " "}).status_code
        == 422
    )
    response = client.post(
        "/api/targets",
        headers=headers,
        json={"name": "Example", "source_url": "https://google.com/maps/place/Example"},
    )
    assert response.status_code == 201
    target = response.json()["id"]
    path = f"/api/targets/{target}/ingestions"
    result = client.post(
        path, headers=headers, json={"csv_text": "rating,review_text\n5,Great"}
    )
    assert result.status_code == 200
    assert result.json()["state"] == "succeeded"
    failed = client.post(
        path, headers=headers, json={"csv_text": "rating,review_text\ninvalid,Text"}
    )
    assert failed.json()["state"] == "failed"
    assert "invalid" not in failed.json()["message"]
    restored = client.get(path + "/latest", headers=headers)
    assert restored.status_code == 200
    assert restored.json() == failed.json()
    with database.connect() as connection:
        persisted = (
            connection.execute(text("SELECT state FROM ingestion_runs")).scalars().all()
        )
        assert sorted(persisted) == ["failed", "succeeded"]
    with Session(database) as db:
        assert len(db.scalars(select(Review)).all()) == 1
        assert len(db.scalars(select(IngestionRun)).all()) == 2
    other_token = make_token(sub="22222222-2222-4222-8222-222222222222")
    other = {"Authorization": f"Bearer {other_token}"}
    assert client.get(path + "/latest", headers=other).status_code == 404
    assert (
        client.post(
            path, headers=other, json={"csv_text": "rating,review_text\n5,Other"}
        ).status_code
        == 404
    )
    with Session(database) as db:
        assert len(db.scalars(select(IngestionRun)).all()) == 2


def test_persistence_error_records_failure(client, make_token, database, caplog):
    from sqlalchemy import event

    headers = {"Authorization": f"Bearer {make_token()}"}
    target = client.post(
        "/api/targets",
        headers=headers,
        json={"name": "Example", "source_url": "https://google.com/maps/place/X"},
    ).json()["id"]

    def fail_reviews(session, context, instances):
        if any(isinstance(item, Review) for item in session.new):
            if session.bind.dialect.name == "postgresql":
                # A real server error aborts the transaction until rollback.
                session.execute(text("SELECT 1 / 0"))
            raise RuntimeError("sensitive database detail")

    event.listen(Session, "before_flush", fail_reviews)
    try:
        response = client.post(
            f"/api/targets/{target}/ingestions",
            headers=headers,
            json={"csv_text": "rating,review_text\n5,Great"},
        )
    finally:
        event.remove(Session, "before_flush", fail_reviews)
    assert response.json()["state"] == "failed"
    assert "sensitive" not in response.text
    assert "Ingestion" in caplog.text and "failed" in caplog.text
    assert "sensitive database detail" not in caplog.text
    assert "SELECT 1 / 0" not in caplog.text
    with Session(database) as db:
        assert not db.scalars(select(Review)).all()
        assert db.scalar(select(IngestionRun)).state == "failed"


@pytest.fixture
def review_access_data(client, make_token, database):
    user_b = UUID("22222222-2222-4222-8222-222222222222")
    with database.begin() as connection:
        connection.execute(
            Base.metadata.tables["auth.users"].insert().values(id=user_b)
        )

    headers = [
        {"Authorization": f"Bearer {make_token(sub=subject)}"}
        for subject in (USER_A_ID, str(user_b))
    ]
    targets = []
    for index, auth in enumerate(headers):
        created = client.post(
            "/api/targets",
            headers=auth,
            json={
                "name": f"Business {index}",
                "source_url": "https://google.com/maps/place/X",
            },
        )
        assert created.status_code == 201
        target_id = created.json()["id"]
        imported = client.post(
            f"/api/targets/{target_id}/ingestions",
            headers=auth,
            json={
                "csv_text": f"rating,review_text\n5,Private {index}\n4,Other {index}"
            },
        )
        assert imported.status_code == 200
        assert imported.json()["state"] == "succeeded"
        targets.append(target_id)
    return headers, targets


def review_storage_snapshot(database):
    """Compare full persisted rows, including existing review text and ratings."""
    with database.connect() as connection:
        return {
            name: connection.execute(
                select(Base.metadata.tables[name]).order_by(
                    Base.metadata.tables[name].c.id
                )
            ).all()
            for name in ("analysis_targets", "reviews", "ingestion_runs")
        }


def test_review_listing_is_scoped_to_authorized_target(
    client, database, review_access_data
):
    headers, targets = review_access_data
    for index, (auth, target_id) in enumerate(zip(headers, targets, strict=True)):
        path = f"/api/targets/{target_id}/reviews"
        response = client.get(path, headers=auth)
        assert response.status_code == 200
        reviews = response.json()
        assert len(reviews) == 2
        assert {row["review_text"] for row in reviews} == {
            f"Private {index}",
            f"Other {index}",
        }
        assert {row["target_id"] for row in reviews} == {target_id}
        assert {row["rating"] for row in reviews} == {4, 5}
        assert all(
            set(row) == {"id", "target_id", "run_id", "review_text", "rating"}
            for row in reviews
        )
        first = client.get(path, headers=auth, params={"limit": 1}).json()
        second = client.get(path, headers=auth, params={"limit": 1, "offset": 1}).json()
        assert first + second == reviews
        assert client.get(path, headers=auth, params={"offset": 2}).json() == []


def test_owned_target_without_reviews_returns_empty_list(client, database, make_token):
    headers = {"Authorization": f"Bearer {make_token()}"}
    target = client.post(
        "/api/targets",
        headers=headers,
        json={"name": "Empty", "source_url": "https://google.com/maps/place/X"},
    ).json()["id"]
    response = client.get(f"/api/targets/{target}/reviews", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("suffix", ["reviews", "ingestions/latest"])
def test_child_reads_hide_other_users_targets(
    client, database, review_access_data, suffix
):
    headers, targets = review_access_data
    before = review_storage_snapshot(database)
    for index, auth in enumerate(headers):
        denied = client.get(
            f"/api/targets/{targets[1 - index]}/{suffix}",
            headers=auth,
            params={"owner_id": USER_A_ID, "target_id": targets[index]},
        )
        missing = client.get(f"/api/targets/{uuid4()}/{suffix}", headers=auth)
        assert denied.status_code == missing.status_code == 404
        assert (
            denied.json() == missing.json() == {"detail": "Analysis target not found."}
        )
    assert review_storage_snapshot(database) == before


def test_cross_user_ingestion_denied_before_processing(
    client, database, review_access_data, monkeypatch
):
    headers, targets = review_access_data
    before = review_storage_snapshot(database)

    def forbidden_parser(*args, **kwargs):
        pytest.fail("Denied ingestion must not parse or process review data")

    monkeypatch.setattr("app.api.targets.parse_csv_reviews", forbidden_parser)
    for index, auth in enumerate(headers):
        response = client.post(
            f"/api/targets/{targets[1 - index]}/ingestions",
            headers=auth,
            json={"csv_text": "rating,review_text\n1,Unauthorized creation"},
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Analysis target not found."}
    assert review_storage_snapshot(database) == before


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_direct_review_writes_are_not_exposed(
    client, database, review_access_data, method
):
    headers, targets = review_access_data
    before = review_storage_snapshot(database)
    with Session(database) as db:
        review_id = db.scalar(
            select(Review.id).where(Review.target_id == UUID(targets[0]))
        )
    for path in (
        f"/api/targets/{targets[0]}/reviews",
        f"/api/targets/{targets[0]}/reviews/{review_id}",
    ):
        response = client.request(
            method,
            path,
            headers=headers[1],
            json={"target_id": targets[0], "rating": 1, "review_text": "Changed"},
        )
        assert response.status_code in (404, 405)
    assert review_storage_snapshot(database) == before


@pytest.mark.parametrize("token", [None, "invalid-token"])
def test_child_requests_require_verified_auth(
    client, database, review_access_data, token
):
    _, targets = review_access_data
    before = review_storage_snapshot(database)
    headers = {} if token is None else {"Authorization": f"Bearer {token}"}
    for method, suffix, body in (
        ("GET", "reviews", None),
        ("GET", "ingestions/latest", None),
        ("POST", "ingestions", {"csv_text": "rating,review_text\n5,Denied"}),
    ):
        response = client.request(
            method, f"/api/targets/{targets[0]}/{suffix}", headers=headers, json=body
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "Authentication required."}
    assert review_storage_snapshot(database) == before


@pytest.mark.parametrize(
    "params", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "invalid"}]
)
def test_review_pagination_validation(client, database, review_access_data, params):
    headers, targets = review_access_data
    response = client.get(
        f"/api/targets/{targets[0]}/reviews", headers=headers[0], params=params
    )
    assert response.status_code == 422

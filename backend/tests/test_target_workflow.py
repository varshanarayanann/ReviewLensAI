import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Column, Table, Uuid, create_engine, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import get_db, to_sqlalchemy_url
from app.models import Base
from app.models.ingestion import IngestionRun, Review
from tests.conftest import USER_A_ID


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

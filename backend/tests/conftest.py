"""DB test fixtures: run against a real local Postgres (astro_test), not SQLite --
JSON columns and other Postgres-specific behavior should be tested against the real
thing. Schema is created directly from the models (not via Alembic) since the two
are equivalent for testing and this avoids running migrations on every test run;
Alembic is for tracking real schema evolution, not test setup.

Each test runs inside a transaction that's rolled back afterward, so tests never
see each other's data and the test database stays empty between runs.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/astro_test"
)

from app.main import app  # noqa: E402  (must come after DATABASE_URL is set)
from app.db import get_db  # noqa: E402
from app.models import Base  # noqa: E402

TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/astro_test"
_engine = create_engine(TEST_DATABASE_URL, future=True)


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.drop_all(bind=_engine)
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def db_session():
    connection = _engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    session: Session = TestingSessionLocal()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        app.dependency_overrides.pop(get_db, None)

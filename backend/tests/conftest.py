"""Pytest fixtures for the SSAT Rankings backend.

Isolation strategy: per-test outer transaction on a dedicated Postgres test DB.
Each test gets a single SQLAlchemy session wrapped in an outer transaction +
re-entrant SAVEPOINT. App code can call `db.commit()` as usual — that just
releases the savepoint; nothing touches the outer transaction. On teardown, we
roll back the outer transaction, discarding all rows the test created.

Assumes `alembic upgrade head` has already been applied to the test DB. Run
once with:
    createdb ssat_test
    TEST_DATABASE_URL=postgresql+psycopg://${USER}@localhost:5432/ssat_test \
        alembic upgrade head
"""
from __future__ import annotations

import getpass
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session as OrmSession, sessionmaker

from app.core.auth import generate_token, hash_token
from app.core.config import settings
from app.db.database import get_db
from app.db.user_models import MagicLinkToken, User
from app.main import app as fastapi_app

# Tests run over http://testserver — Secure cookies would never be sent back.
# Force debug=True so cookies aren't marked Secure.
settings.debug = True

# Force model imports so SQLAlchemy's metadata knows every table (not strictly
# needed since alembic already created the schema, but keeps us honest).
import app.db.models  # noqa: F401
import app.db.stats_models  # noqa: F401
import app.db.user_models  # noqa: F401


TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    f"postgresql+psycopg://{getpass.getuser()}@localhost:5432/ssat_test",
)


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Function-scoped DB session. Wraps the whole test in an outer transaction
    that rolls back on teardown. The app's `get_db` dependency yields the same
    session so test writes and app writes are in one transaction."""
    connection = test_engine.connect()
    transaction = connection.begin()
    SessionCls = sessionmaker(bind=connection, expire_on_commit=False)
    session: OrmSession = SessionCls()
    session.begin_nested()

    # App calls `session.commit()` which releases the SAVEPOINT without
    # committing the outer transaction. Restart a savepoint each time so
    # subsequent commits in the same test keep working.
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session_, transaction_):
        if transaction_.nested and not transaction_._parent.nested:
            session_.begin_nested()

    def override_get_db():
        yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        yield session
    finally:
        fastapi_app.dependency_overrides.pop(get_db, None)
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    """TestClient with get_db overridden (via db_session fixture)."""
    return TestClient(fastapi_app)


# ---------- autouse mocks: isolate from external effects ----------


@pytest.fixture(autouse=True)
def mock_send_magic_link(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("app.api.routes.auth.send_magic_link", mock)
    return mock


_STUB_PLAYERS = [
    {
        "id": 1, "name": "Alpha", "team": "AAA", "position": "DL",
        "games_played": 17, "overall_score": 100.0, "position_group": "DEF",
        "category_scores": {"run_defense": 90, "pass_rush": 85, "coverage": 80, "playmaking": 70},
        "stats": {},
    },
    {
        "id": 2, "name": "Bravo", "team": "BBB", "position": "LB",
        "games_played": 15, "overall_score": 85.0, "position_group": "DEF",
        "category_scores": {"run_defense": 80, "pass_rush": 75, "coverage": 75, "playmaking": 70},
        "stats": {},
    },
    {
        "id": 3, "name": "Charlie", "team": "CCC", "position": "CB",
        "games_played": 10, "overall_score": 70.0, "position_group": "DEF",
        "category_scores": {"run_defense": 70, "pass_rush": 65, "coverage": 75, "playmaking": 70},
        "stats": {},
    },
]


@pytest.fixture(autouse=True)
def mock_rankings_compute(monkeypatch):
    """Stub process_player_rankings so tests don't need real NFL data.
    Returns a fresh copy each call so mutations in one test don't leak."""

    def _stub(*_args, **_kwargs):
        return [dict(p) for p in _STUB_PLAYERS]

    mock = MagicMock(side_effect=_stub)
    monkeypatch.setattr(
        "app.api.routes.saved_rankings.process_player_rankings", mock
    )
    # pff path — some tests may hit it via source='pff'; return empty to keep
    # behavior deterministic.
    monkeypatch.setattr(
        "app.api.routes.saved_rankings.process_pff_rankings",
        MagicMock(return_value=[]),
    )
    return mock


# ---------- helpers ----------


def _seed_user(db: OrmSession, email: str) -> User:
    user = User(email=email)
    db.add(user)
    db.flush()
    return user


def _sign_in(client: TestClient, db: OrmSession, email: str) -> User:
    """Create a user and mint a magic link, then exchange it for a session
    cookie via the real /verify endpoint. The cookie is stored on the client."""
    user = _seed_user(db, email)
    raw = generate_token()
    db.add(
        MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
    )
    db.flush()
    r = client.post("/api/auth/verify", json={"token": raw})
    assert r.status_code == 200, r.text
    return user


@pytest.fixture
def auth_client(client, db_session):
    """TestClient pre-authenticated as test@example.com."""
    user = _sign_in(client, db_session, "test@example.com")
    client.seeded_user = user  # type: ignore[attr-defined]
    return client


@pytest.fixture
def second_user(db_session) -> User:
    """A separate user for tenant-isolation tests. Not signed in."""
    return _seed_user(db_session, "other@example.com")


@pytest.fixture
def second_client(test_engine, db_session):
    """A second TestClient pre-authenticated as other@example.com. Shares the
    same db_session/dependency override as `client`, so both clients see the
    same transactional state."""
    c = TestClient(fastapi_app)
    user = _sign_in(c, db_session, "other@example.com")
    c.seeded_user = user  # type: ignore[attr-defined]
    return c

"""Tests for /api/auth/* magic-link flow."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.core.auth import generate_token, hash_token
from app.core.config import settings
from app.db.user_models import MagicLinkToken, Session as SessionRow, User


# ---------------- request-link ----------------


def test_request_link_new_email_creates_user_and_token(client, db_session, mock_send_magic_link):
    r = client.post("/api/auth/request-link", json={"email": "new@example.com"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}

    user = db_session.query(User).filter(User.email == "new@example.com").first()
    assert user is not None
    tokens = db_session.query(MagicLinkToken).filter(MagicLinkToken.user_id == user.id).all()
    assert len(tokens) == 1
    assert tokens[0].consumed_at is None
    assert tokens[0].expires_at > datetime.now(timezone.utc)

    assert mock_send_magic_link.call_count == 1
    called_email, called_url = mock_send_magic_link.call_args[0]
    assert called_email == "new@example.com"
    assert called_url.startswith(settings.app_url.rstrip("/") + "/verify?token=")


def test_request_link_existing_email_no_duplicate_user(client, db_session, mock_send_magic_link):
    # Seed a user via the endpoint, then request again.
    client.post("/api/auth/request-link", json={"email": "repeat@example.com"})
    client.post("/api/auth/request-link", json={"email": "repeat@example.com"})

    users = db_session.query(User).filter(User.email == "repeat@example.com").all()
    assert len(users) == 1
    tokens = (
        db_session.query(MagicLinkToken).filter(MagicLinkToken.user_id == users[0].id).all()
    )
    assert len(tokens) == 2
    assert mock_send_magic_link.call_count == 2


def test_request_link_rejects_invalid_email(client):
    r = client.post("/api/auth/request-link", json={"email": "not-an-email"})
    assert r.status_code == 422


def test_request_link_email_is_case_insensitive(client, db_session):
    # citext column — same user regardless of case
    client.post("/api/auth/request-link", json={"email": "Mixed@Example.com"})
    client.post("/api/auth/request-link", json={"email": "mixed@example.com"})

    users = db_session.query(User).filter(User.email == "mixed@example.com").all()
    assert len(users) == 1


# ---------------- verify ----------------


def _mint_token(db_session, user: User, *, expires_in_minutes: int = 5, consumed: bool = False) -> str:
    raw = generate_token()
    row = MagicLinkToken(
        user_id=user.id,
        token_hash=hash_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes),
        consumed_at=datetime.now(timezone.utc) if consumed else None,
    )
    db_session.add(row)
    db_session.flush()
    return raw


def test_verify_valid_token(client, db_session):
    user = User(email="v@example.com")
    db_session.add(user)
    db_session.flush()
    raw = _mint_token(db_session, user)

    r = client.post("/api/auth/verify", json={"token": raw})
    assert r.status_code == 200, r.text
    assert r.json() == {"user": {"id": user.id, "email": "v@example.com"}}

    # Cookie set
    assert settings.session_cookie_name in client.cookies

    # Token consumed
    token = db_session.query(MagicLinkToken).filter(
        MagicLinkToken.token_hash == hash_token(raw)
    ).one()
    assert token.consumed_at is not None

    # Session row exists
    sessions = db_session.query(SessionRow).filter(SessionRow.user_id == user.id).all()
    assert len(sessions) == 1
    assert sessions[0].expires_at > datetime.now(timezone.utc) + timedelta(days=29)


def test_verify_consumed_token_rejected(client, db_session):
    user = User(email="c@example.com")
    db_session.add(user)
    db_session.flush()
    raw = _mint_token(db_session, user, consumed=True)

    r = client.post("/api/auth/verify", json={"token": raw})
    assert r.status_code == 400


def test_verify_expired_token_rejected(client, db_session):
    user = User(email="e@example.com")
    db_session.add(user)
    db_session.flush()
    raw = _mint_token(db_session, user, expires_in_minutes=-1)

    r = client.post("/api/auth/verify", json={"token": raw})
    assert r.status_code == 400


def test_verify_unknown_token_rejected(client):
    r = client.post("/api/auth/verify", json={"token": "totally-not-a-real-token"})
    assert r.status_code == 400


# ---------------- logout ----------------


def test_logout_clears_cookie_and_deletes_session(auth_client, db_session):
    user_id = auth_client.seeded_user.id

    # Pre: session row exists
    assert db_session.query(SessionRow).filter(SessionRow.user_id == user_id).count() == 1

    r = auth_client.post("/api/auth/logout")
    assert r.status_code == 200
    assert r.json() == {"ok": True}

    # Session deleted
    assert db_session.query(SessionRow).filter(SessionRow.user_id == user_id).count() == 0


def test_logout_without_cookie_is_noop(client):
    r = client.post("/api/auth/logout")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


# ---------------- /me ----------------


def test_me_with_valid_cookie(auth_client):
    r = auth_client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "test@example.com"


def test_me_without_cookie_401(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_with_expired_session_401(auth_client, db_session):
    # Expire the session row in place
    user_id = auth_client.seeded_user.id
    session_row = db_session.query(SessionRow).filter(SessionRow.user_id == user_id).one()
    session_row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.flush()

    r = auth_client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_with_deleted_session_401(auth_client, db_session):
    user_id = auth_client.seeded_user.id
    db_session.query(SessionRow).filter(SessionRow.user_id == user_id).delete()
    db_session.flush()

    r = auth_client.get("/api/auth/me")
    assert r.status_code == 401

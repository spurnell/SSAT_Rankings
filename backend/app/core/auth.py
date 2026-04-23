"""Cookie-based session auth for magic-link login."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session as OrmSession

from app.core.config import settings
from app.db.database import get_db
from app.db.user_models import Session as SessionRow, User


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _lookup_session(db: OrmSession, cookie_value: str) -> Optional[User]:
    token_hash = hash_token(cookie_value)
    row = (
        db.query(SessionRow)
        .filter(
            SessionRow.token_hash == token_hash,
            SessionRow.expires_at > _now(),
        )
        .first()
    )
    if not row:
        return None
    return db.query(User).filter(User.id == row.user_id).first()


def get_current_user(
    session_cookie: Optional[str] = Cookie(None, alias=settings.session_cookie_name),
    db: OrmSession = Depends(get_db),
) -> User:
    """Requires a valid session cookie. Raises 401 otherwise."""
    if not session_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not signed in")
    user = _lookup_session(db, session_cookie)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid session")
    return user


def get_optional_user(
    session_cookie: Optional[str] = Cookie(None, alias=settings.session_cookie_name),
    db: OrmSession = Depends(get_db),
) -> Optional[User]:
    """Returns the user if the cookie is valid, else None. Does not raise."""
    if not session_cookie:
        return None
    return _lookup_session(db, session_cookie)

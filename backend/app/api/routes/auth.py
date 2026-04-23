"""Magic-link auth routes.

Flow:
  POST /api/auth/request-link   — email → always 200, link sent if resend is configured
  POST /api/auth/verify         — token → session cookie set, returns user
  POST /api/auth/logout         — deletes session row + clears cookie
  GET  /api/auth/me             — returns current user or 401
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session as OrmSession

from app.core.auth import generate_token, get_current_user, hash_token
from app.core.config import settings
from app.db.database import get_db
from app.db.user_models import MagicLinkToken, Session as SessionRow, User
from app.services.email import send_magic_link

router = APIRouter(prefix="/auth", tags=["auth"])


TOKEN_TTL = timedelta(minutes=15)
SESSION_TTL = timedelta(days=30)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RequestLinkBody(BaseModel):
    email: EmailStr


class VerifyBody(BaseModel):
    token: str


class UserResponse(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True


class VerifyResponse(BaseModel):
    user: UserResponse


class OkResponse(BaseModel):
    ok: bool = True


def _set_session_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        path="/",
    )


@router.post("/request-link", response_model=OkResponse)
def request_link(body: RequestLinkBody, db: OrmSession = Depends(get_db)) -> OkResponse:
    email = str(body.email).strip()
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(email=email)
        db.add(user)
        db.flush()

    raw_token = generate_token()
    db.add(
        MagicLinkToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=_now() + TOKEN_TTL,
        )
    )
    db.commit()

    link = f"{settings.app_url.rstrip('/')}/verify?token={raw_token}"
    send_magic_link(email, link)

    # Never leak whether the email existed — always return success.
    return OkResponse()


@router.post("/verify", response_model=VerifyResponse)
def verify(
    body: VerifyBody,
    response: Response,
    db: OrmSession = Depends(get_db),
) -> VerifyResponse:
    token_hash = hash_token(body.token)
    row = (
        db.query(MagicLinkToken)
        .filter(
            MagicLinkToken.token_hash == token_hash,
            MagicLinkToken.consumed_at.is_(None),
            MagicLinkToken.expires_at > _now(),
        )
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid or expired token",
        )

    row.consumed_at = _now()

    raw_session = generate_token()
    db.add(
        SessionRow(
            user_id=row.user_id,
            token_hash=hash_token(raw_session),
            expires_at=_now() + SESSION_TTL,
        )
    )
    db.commit()

    _set_session_cookie(response, raw_session)
    user = db.query(User).filter(User.id == row.user_id).first()
    return VerifyResponse(user=UserResponse.model_validate(user))


@router.post("/logout", response_model=OkResponse)
def logout(
    response: Response,
    session_cookie: Optional[str] = Cookie(None, alias=settings.session_cookie_name),
    db: OrmSession = Depends(get_db),
) -> OkResponse:
    if session_cookie:
        db.query(SessionRow).filter(
            SessionRow.token_hash == hash_token(session_cookie)
        ).delete(synchronize_session=False)
        db.commit()
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=not settings.debug,
        samesite="lax",
    )
    return OkResponse()


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)

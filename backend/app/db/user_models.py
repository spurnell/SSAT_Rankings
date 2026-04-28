"""Auth + saved-rankings models — Postgres only (citext, jsonb)."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, Text, DateTime, ForeignKey, CheckConstraint, Index,
)
from sqlalchemy.dialects.postgresql import JSONB, CITEXT
from sqlalchemy.orm import relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(CITEXT(), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    tokens = relationship(
        "MagicLinkToken", back_populates="user", cascade="all, delete-orphan"
    )
    sessions = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    saved_rankings = relationship(
        "SavedRanking", back_populates="user", cascade="all, delete-orphan"
    )


class MagicLinkToken(Base):
    __tablename__ = "magic_link_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash = Column(Text, nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="tokens")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash = Column(Text, nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="sessions")


class SavedRanking(Base):
    __tablename__ = "saved_rankings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(Text, nullable=False)

    # Ranking config (matches /api/calculate inputs)
    position_group = Column(Text, nullable=False)
    # weights is null when the ranking uses user-defined categories instead.
    weights = Column(JSONB, nullable=True)
    # User-defined categories (custom-category builder). Null for default-category rankings.
    # Shape: [{"id": str, "name": str, "weight": float,
    #          "stats": [{"source": str, "name": str}, ...]}, ...]
    categories = Column(JSONB, nullable=True)
    min_games = Column(Integer, nullable=True)
    mode = Column(Text, nullable=True)  # "season" | "cumulative" | "per_game"
    min_seasons = Column(Integer, nullable=True)
    position_filter = Column(Text, nullable=True)
    source = Column(Text, nullable=True)

    # Sharing
    share_mode = Column(Text, nullable=False, server_default="none")
    share_slug = Column(Text, nullable=True, unique=True)
    results_json = Column(JSONB, nullable=True)  # populated only when share_mode='frozen'
    results_computed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "share_mode in ('none','live','frozen')",
            name="ck_saved_rankings_share_mode",
        ),
        Index("ix_saved_rankings_user_id", "user_id"),
    )

    user = relationship("User", back_populates="saved_rankings")

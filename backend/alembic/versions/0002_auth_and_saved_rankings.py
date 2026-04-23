"""auth + saved rankings

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, CITEXT


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", CITEXT(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "magic_link_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("token_hash", name="uq_magic_link_tokens_token_hash"),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("token_hash", name="uq_sessions_token_hash"),
    )

    op.create_table(
        "saved_rankings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("position_group", sa.Text(), nullable=False),
        sa.Column("weights", JSONB(), nullable=False),
        sa.Column("min_games", sa.Integer(), nullable=True),
        sa.Column("mode", sa.Text(), nullable=True),
        sa.Column("min_seasons", sa.Integer(), nullable=True),
        sa.Column("position_filter", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column(
            "share_mode",
            sa.Text(),
            server_default="none",
            nullable=False,
        ),
        sa.Column("share_slug", sa.Text(), nullable=True),
        sa.Column("results_json", JSONB(), nullable=True),
        sa.Column("results_computed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("share_slug", name="uq_saved_rankings_share_slug"),
        sa.CheckConstraint(
            "share_mode in ('none','live','frozen')",
            name="ck_saved_rankings_share_mode",
        ),
    )
    op.create_index(
        "ix_saved_rankings_user_id", "saved_rankings", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_saved_rankings_user_id", table_name="saved_rankings")
    op.drop_table("saved_rankings")
    op.drop_table("sessions")
    op.drop_table("magic_link_tokens")
    op.drop_table("users")

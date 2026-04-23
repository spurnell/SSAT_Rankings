"""initial — blog, players, player_season_stats, ingestion_log

Revision ID: 0001
Revises:
Create Date: 2026-04-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "blog_posts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("post_type", sa.String(length=50), nullable=False),
        sa.Column("featured_players", sa.JSON(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=True),
    )
    op.create_index("ix_blog_posts_slug", "blog_posts", ["slug"], unique=True)

    op.create_table(
        "players",
        sa.Column("gsis_id", sa.String(length=20), primary_key=True),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("position", sa.String(length=10), nullable=False),
        sa.Column("position_group", sa.String(length=5), nullable=False),
        sa.Column("team", sa.String(length=5), nullable=True),
        sa.Column("headshot_url", sa.Text(), nullable=True),
    )

    op.create_table(
        "player_season_stats",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("gsis_id", sa.String(length=20), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("team", sa.String(length=5), nullable=True),
        sa.Column("games_played", sa.Integer(), server_default="0"),
        # Passing
        sa.Column("completions", sa.Float(), server_default="0"),
        sa.Column("attempts", sa.Float(), server_default="0"),
        sa.Column("passing_yards", sa.Float(), server_default="0"),
        sa.Column("passing_tds", sa.Float(), server_default="0"),
        sa.Column("interceptions", sa.Float(), server_default="0"),
        sa.Column("sacks", sa.Float(), server_default="0"),
        sa.Column("sack_yards", sa.Float(), server_default="0"),
        sa.Column("passing_first_downs", sa.Float(), server_default="0"),
        sa.Column("sack_fumbles", sa.Float(), server_default="0"),
        # Rushing
        sa.Column("carries", sa.Float(), server_default="0"),
        sa.Column("rushing_yards", sa.Float(), server_default="0"),
        sa.Column("rushing_tds", sa.Float(), server_default="0"),
        sa.Column("rushing_first_downs", sa.Float(), server_default="0"),
        sa.Column("rushing_fumbles", sa.Float(), server_default="0"),
        sa.Column("longest_rush", sa.Float(), server_default="0"),
        # Receiving
        sa.Column("receptions", sa.Float(), server_default="0"),
        sa.Column("targets", sa.Float(), server_default="0"),
        sa.Column("receiving_yards", sa.Float(), server_default="0"),
        sa.Column("receiving_tds", sa.Float(), server_default="0"),
        sa.Column("receiving_fumbles", sa.Float(), server_default="0"),
        sa.Column("receiving_first_downs", sa.Float(), server_default="0"),
        sa.Column("receiving_yards_after_catch", sa.Float(), server_default="0"),
        sa.Column("longest_reception", sa.Float(), server_default="0"),
        # Defense
        sa.Column("tackles", sa.Float(), server_default="0"),
        sa.Column("solo_tackles", sa.Float(), server_default="0"),
        sa.Column("assists", sa.Float(), server_default="0"),
        sa.Column("def_sacks", sa.Float(), server_default="0"),
        sa.Column("qb_hits", sa.Float(), server_default="0"),
        sa.Column("tackles_for_loss", sa.Float(), server_default="0"),
        sa.Column("passes_defended", sa.Float(), server_default="0"),
        sa.Column("def_interceptions", sa.Float(), server_default="0"),
        sa.Column("forced_fumbles", sa.Float(), server_default="0"),
        sa.Column("fumble_recoveries", sa.Float(), server_default="0"),
        sa.Column("defensive_tds", sa.Float(), server_default="0"),
        # Kicking
        sa.Column("fg_made", sa.Float(), server_default="0"),
        sa.Column("fg_attempts", sa.Float(), server_default="0"),
        sa.Column("fg_made_40_49", sa.Float(), server_default="0"),
        sa.Column("fg_made_50_plus", sa.Float(), server_default="0"),
        sa.Column("long_fg", sa.Float(), server_default="0"),
        sa.Column("xp_made", sa.Float(), server_default="0"),
        sa.Column("xp_attempts", sa.Float(), server_default="0"),
        sa.Column("kicking_points", sa.Float(), server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("gsis_id", "season", name="uq_player_season"),
    )
    op.create_index(
        "ix_player_season_stats_gsis_id", "player_season_stats", ["gsis_id"]
    )
    op.create_index("ix_season", "player_season_stats", ["season"])

    op.create_table(
        "ingestion_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("data_type", sa.String(length=50), nullable=False),
        sa.Column("rows_ingested", sa.Integer(), server_default="0"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("ingestion_log")
    op.drop_index("ix_season", table_name="player_season_stats")
    op.drop_index("ix_player_season_stats_gsis_id", table_name="player_season_stats")
    op.drop_table("player_season_stats")
    op.drop_table("players")
    op.drop_index("ix_blog_posts_slug", table_name="blog_posts")
    op.drop_table("blog_posts")

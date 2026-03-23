"""
SQLAlchemy models for NFL player stats stored in rankings.db.

Tables:
- players: Player identity (gsis_id, name, position, team)
- player_season_stats: Wide stats table for all position groups per season
- ingestion_log: Tracks data refresh runs
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, String, Text, DateTime,
    UniqueConstraint, Index,
)
from app.db.database import RankingsBase


class Player(RankingsBase):
    __tablename__ = "players"

    gsis_id = Column(String(20), primary_key=True)
    display_name = Column(String(200), nullable=False)
    position = Column(String(10), nullable=False)
    position_group = Column(String(5), nullable=False)  # DEF, QB, RB, WR, TE, K
    team = Column(String(5))
    headshot_url = Column(Text)

    def __repr__(self):
        return f"<Player({self.gsis_id}, {self.display_name}, {self.position})>"


class PlayerSeasonStats(RankingsBase):
    __tablename__ = "player_season_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gsis_id = Column(String(20), nullable=False, index=True)
    season = Column(Integer, nullable=False)
    games_played = Column(Integer, default=0)

    # --- Passing stats (QB) ---
    completions = Column(Float, default=0)
    attempts = Column(Float, default=0)
    passing_yards = Column(Float, default=0)
    passing_tds = Column(Float, default=0)
    interceptions = Column(Float, default=0)
    sacks = Column(Float, default=0)
    sack_yards = Column(Float, default=0)
    passing_first_downs = Column(Float, default=0)
    sack_fumbles = Column(Float, default=0)

    # --- Rushing stats (RB, QB) ---
    carries = Column(Float, default=0)
    rushing_yards = Column(Float, default=0)
    rushing_tds = Column(Float, default=0)
    rushing_first_downs = Column(Float, default=0)
    rushing_fumbles = Column(Float, default=0)
    longest_rush = Column(Float, default=0)

    # --- Receiving stats (WR, TE, RB) ---
    receptions = Column(Float, default=0)
    targets = Column(Float, default=0)
    receiving_yards = Column(Float, default=0)
    receiving_tds = Column(Float, default=0)
    receiving_fumbles = Column(Float, default=0)
    receiving_first_downs = Column(Float, default=0)
    receiving_yards_after_catch = Column(Float, default=0)
    longest_reception = Column(Float, default=0)

    # --- Defensive stats (DEF, from PBP aggregation) ---
    tackles = Column(Float, default=0)
    solo_tackles = Column(Float, default=0)
    assists = Column(Float, default=0)
    def_sacks = Column(Float, default=0)
    qb_hits = Column(Float, default=0)
    tackles_for_loss = Column(Float, default=0)
    passes_defended = Column(Float, default=0)
    def_interceptions = Column(Float, default=0)
    forced_fumbles = Column(Float, default=0)
    fumble_recoveries = Column(Float, default=0)
    defensive_tds = Column(Float, default=0)

    # --- Kicking stats (K, from PBP aggregation) ---
    fg_made = Column(Float, default=0)
    fg_attempts = Column(Float, default=0)
    fg_made_40_49 = Column(Float, default=0)
    fg_made_50_plus = Column(Float, default=0)
    long_fg = Column(Float, default=0)
    xp_made = Column(Float, default=0)
    xp_attempts = Column(Float, default=0)
    kicking_points = Column(Float, default=0)

    # --- Metadata ---
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("gsis_id", "season", name="uq_player_season"),
        Index("ix_season", "season"),
    )

    def __repr__(self):
        return f"<PlayerSeasonStats({self.gsis_id}, season={self.season})>"


class IngestionLog(RankingsBase):
    __tablename__ = "ingestion_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    season = Column(Integer, nullable=False)
    data_type = Column(String(50), nullable=False)  # "players", "seasonal", "pbp_defense", "pbp_kicking"
    rows_ingested = Column(Integer, default=0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    status = Column(String(20))  # "success", "error"
    error_message = Column(Text)

    def __repr__(self):
        return f"<IngestionLog({self.data_type}, season={self.season}, status={self.status})>"

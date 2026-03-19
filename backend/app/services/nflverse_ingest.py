"""
nflverse data ingestion service.

Fetches NFL data from nflreadpy (nflverse) and writes to the rankings SQLite database.
Called via CLI command, not on every API request.

Uses nflreadpy.load_player_stats() which provides weekly stats for ALL position groups
(offense, defense, kicking) in a single call. We aggregate to seasonal totals.
"""

import nflreadpy as nflr
import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import text

from app.db.database import RankingsSessionLocal, init_rankings_db
from app.db.stats_models import Player, PlayerSeasonStats, IngestionLog


# Map nflverse positions to our position groups
POSITION_TO_GROUP = {
    # Defensive
    "DE": "DEF", "DT": "DEF", "NT": "DEF",
    "OLB": "DEF", "ILB": "DEF", "MLB": "DEF", "LB": "DEF",
    "CB": "DEF", "FS": "DEF", "SS": "DEF", "S": "DEF", "DB": "DEF",
    "EDGE": "DEF", "SAF": "DEF", "DL": "DEF",
    # Offensive
    "QB": "QB",
    "RB": "RB", "FB": "RB", "HB": "RB",
    "WR": "WR",
    "TE": "TE",
    # Special teams
    "K": "K",
}

# nflreadpy position_group values -> our position groups
NFLREADPY_GROUP_MAP = {
    "DB": "DEF", "DL": "DEF", "LB": "DEF",
    "QB": "QB", "RB": "RB", "WR": "WR", "TE": "TE",
    # K has position_group "SPEC" in nflreadpy, handled via position column
}


def _log_ingestion(session, season, data_type, rows, status, error=None, started_at=None):
    """Log an ingestion run."""
    log = IngestionLog(
        season=season,
        data_type=data_type,
        rows_ingested=rows,
        started_at=started_at or datetime.utcnow(),
        completed_at=datetime.utcnow(),
        status=status,
        error_message=error,
    )
    session.add(log)
    session.commit()


def ingest_players():
    """Fetch player roster from nflverse and upsert into players table."""
    init_rankings_db()
    session = RankingsSessionLocal()
    started = datetime.utcnow()

    try:
        print("Fetching player roster from nflverse...")
        players_df = nfl.import_players()

        # Filter to players with a gsis_id and relevant position
        players_df = players_df.dropna(subset=["gsis_id", "position"])
        players_df = players_df[players_df["position"].isin(POSITION_TO_GROUP.keys())]

        count = 0
        for _, row in players_df.iterrows():
            gsis_id = row["gsis_id"]
            position = row["position"]
            position_group = POSITION_TO_GROUP.get(position, "")
            if not position_group:
                continue

            existing = session.get(Player, gsis_id)
            if existing:
                existing.display_name = row.get("display_name", existing.display_name)
                existing.position = position
                existing.position_group = position_group
                existing.team = row.get("latest_team") or existing.team
                existing.headshot_url = row.get("headshot") or existing.headshot_url
            else:
                session.add(Player(
                    gsis_id=gsis_id,
                    display_name=row.get("display_name", "Unknown"),
                    position=position,
                    position_group=position_group,
                    team=row.get("latest_team"),
                    headshot_url=row.get("headshot"),
                ))
            count += 1

        session.commit()
        print(f"Ingested {count} players.")
        _log_ingestion(session, 0, "players", count, "success", started_at=started)
        return count

    except Exception as e:
        session.rollback()
        print(f"Error ingesting players: {e}")
        _log_ingestion(session, 0, "players", 0, "error", str(e), started_at=started)
        raise
    finally:
        session.close()


def ingest_all_stats(seasons: list[int]):
    """
    Fetch all player stats from nflreadpy and write to database.

    Uses load_player_stats() which returns weekly stats for ALL positions
    (offense, defense, kicking) in a single call. Aggregates to seasonal totals.
    """
    init_rankings_db()
    session = RankingsSessionLocal()
    started = datetime.utcnow()

    try:
        print(f"Fetching player stats from nflreadpy for {seasons}...")
        stats_pl = nflr.load_player_stats(seasons)

        # Filter to regular season
        import polars as pl
        stats_pl = stats_pl.filter(pl.col("season_type") == "REG")

        # Convert to pandas for DB operations
        df = stats_pl.to_pandas()
        print(f"Processing {len(df)} weekly stat rows...")

        if df.empty:
            print("No stats returned.")
            return 0

        # --- Upsert players from stats data ---
        print("Upserting players from stats data...")
        player_cols = ["player_id", "player_display_name", "position", "position_group", "team", "headshot_url"]
        players_df = df[player_cols].drop_duplicates(subset=["player_id"]).dropna(subset=["player_id"])

        player_count = 0
        for _, row in players_df.iterrows():
            pid = row["player_id"]
            position = row.get("position") or ""
            # Determine our position group
            pos_group = POSITION_TO_GROUP.get(position, "")
            if not pos_group:
                # Try nflreadpy's position_group mapping
                nflr_group = row.get("position_group") or ""
                pos_group = NFLREADPY_GROUP_MAP.get(nflr_group, "")
            if not pos_group:
                continue

            existing = session.get(Player, pid)
            if existing:
                existing.display_name = row.get("player_display_name") or existing.display_name
                existing.position = position or existing.position
                existing.position_group = pos_group
                existing.team = row.get("team") or existing.team
                existing.headshot_url = row.get("headshot_url") or existing.headshot_url
            else:
                session.add(Player(
                    gsis_id=pid,
                    display_name=row.get("player_display_name") or "Unknown",
                    position=position,
                    position_group=pos_group,
                    team=row.get("team"),
                    headshot_url=row.get("headshot_url"),
                ))
            player_count += 1

        session.commit()
        print(f"Upserted {player_count} players.")

        # --- Aggregate weekly stats to seasonal totals ---
        print("Aggregating weekly stats to seasonal totals...")

        # Define aggregation rules
        sum_cols = [
            # Passing
            "completions", "attempts", "passing_yards", "passing_tds",
            "passing_interceptions", "sacks_suffered", "sack_yards_lost",
            "passing_first_downs", "sack_fumbles",
            # Rushing
            "carries", "rushing_yards", "rushing_tds",
            "rushing_first_downs", "rushing_fumbles",
            # Receiving
            "receptions", "targets", "receiving_yards", "receiving_tds",
            "receiving_fumbles", "receiving_first_downs",
            "receiving_yards_after_catch",
            # Defensive
            "def_tackles_solo", "def_tackle_assists", "def_sacks",
            "def_qb_hits", "def_tackles_for_loss", "def_pass_defended",
            "def_interceptions", "def_fumbles_forced",
            "fumble_recovery_opp", "def_tds",
            # Kicking
            "fg_made", "fg_att", "fg_made_40_49",
            "fg_made_50_59", "fg_made_60_",
            "pat_made", "pat_att",
        ]
        max_cols = ["fg_long"]

        # Fill NaN with 0 for aggregation
        for col in sum_cols + max_cols:
            if col in df.columns:
                df[col] = df[col].fillna(0)

        # Build aggregation dict
        agg_dict = {}
        for col in sum_cols:
            if col in df.columns:
                agg_dict[col] = "sum"
        for col in max_cols:
            if col in df.columns:
                agg_dict[col] = "max"
        agg_dict["game_id"] = "nunique"  # games played

        seasonal = df.groupby(["player_id", "season"]).agg(agg_dict).reset_index()
        seasonal = seasonal.rename(columns={"game_id": "games_played"})

        print(f"Aggregated to {len(seasonal)} player-seasons.")

        # --- Write to database ---
        count = 0
        for _, row in seasonal.iterrows():
            pid = row["player_id"]
            season_val = int(row["season"])

            player = session.get(Player, pid)
            if not player:
                continue

            games = int(row.get("games_played", 0))
            if games == 0:
                continue

            existing = session.query(PlayerSeasonStats).filter_by(
                gsis_id=pid, season=season_val
            ).first()

            if not existing:
                existing = PlayerSeasonStats(gsis_id=pid, season=season_val)
                session.add(existing)

            existing.games_played = games

            # Passing (column name mapping: nflreadpy → our DB)
            existing.completions = _safe(row, "completions")
            existing.attempts = _safe(row, "attempts")
            existing.passing_yards = _safe(row, "passing_yards")
            existing.passing_tds = _safe(row, "passing_tds")
            existing.interceptions = _safe(row, "passing_interceptions")
            existing.sacks = _safe(row, "sacks_suffered")
            existing.sack_yards = _safe(row, "sack_yards_lost")
            existing.passing_first_downs = _safe(row, "passing_first_downs")
            existing.sack_fumbles = _safe(row, "sack_fumbles")

            # Rushing
            existing.carries = _safe(row, "carries")
            existing.rushing_yards = _safe(row, "rushing_yards")
            existing.rushing_tds = _safe(row, "rushing_tds")
            existing.rushing_first_downs = _safe(row, "rushing_first_downs")
            existing.rushing_fumbles = _safe(row, "rushing_fumbles")

            # Receiving
            existing.receptions = _safe(row, "receptions")
            existing.targets = _safe(row, "targets")
            existing.receiving_yards = _safe(row, "receiving_yards")
            existing.receiving_tds = _safe(row, "receiving_tds")
            existing.receiving_fumbles = _safe(row, "receiving_fumbles")
            existing.receiving_first_downs = _safe(row, "receiving_first_downs")
            existing.receiving_yards_after_catch = _safe(row, "receiving_yards_after_catch")

            # Defensive (column name mapping: nflreadpy → our DB)
            existing.solo_tackles = _safe(row, "def_tackles_solo")
            existing.assists = _safe(row, "def_tackle_assists")
            existing.tackles = _safe(row, "def_tackles_solo") + _safe(row, "def_tackle_assists")
            existing.def_sacks = _safe(row, "def_sacks")
            existing.qb_hits = _safe(row, "def_qb_hits")
            existing.tackles_for_loss = _safe(row, "def_tackles_for_loss")
            existing.passes_defended = _safe(row, "def_pass_defended")
            existing.def_interceptions = _safe(row, "def_interceptions")
            existing.forced_fumbles = _safe(row, "def_fumbles_forced")
            existing.fumble_recoveries = _safe(row, "fumble_recovery_opp")
            existing.defensive_tds = _safe(row, "def_tds")

            # Kicking (column name mapping: nflreadpy → our DB)
            existing.fg_made = _safe(row, "fg_made")
            existing.fg_attempts = _safe(row, "fg_att")
            existing.fg_made_40_49 = _safe(row, "fg_made_40_49")
            existing.fg_made_50_plus = _safe(row, "fg_made_50_59") + _safe(row, "fg_made_60_")
            existing.long_fg = _safe(row, "fg_long")
            existing.xp_made = _safe(row, "pat_made")
            existing.xp_attempts = _safe(row, "pat_att")
            existing.kicking_points = _safe(row, "fg_made") * 3 + _safe(row, "pat_made")

            existing.updated_at = datetime.utcnow()
            count += 1

        session.commit()
        print(f"Ingested stats for {count} player-seasons.")
        for s in seasons:
            _log_ingestion(session, s, "nflreadpy_all", count, "success", started_at=started)
        return count

    except Exception as e:
        session.rollback()
        print(f"Error ingesting stats: {e}")
        import traceback
        traceback.print_exc()
        for s in seasons:
            _log_ingestion(session, s, "nflreadpy_all", 0, "error", str(e), started_at=started)
        raise
    finally:
        session.close()


def refresh_all(season: int):
    """Run full data refresh for a given season."""
    print(f"\n{'='*60}")
    print(f"  SSAT Rankings Data Refresh — Season {season}")
    print(f"{'='*60}\n")

    init_rankings_db()

    print("Step 1/2: Ingesting player roster...")
    ingest_players()

    print(f"\nStep 2/2: Ingesting all stats from nflreadpy...")
    ingest_all_stats([season])

    print(f"\n{'='*60}")
    print(f"  Refresh complete for season {season}!")
    print(f"{'='*60}\n")


# --- Helper functions ---

def _safe(row, col, default=0.0):
    """Safely extract a float from a pandas row."""
    val = row.get(col, default)
    if pd.isna(val):
        return default
    return float(val)

"""
nflverse data ingestion service.

Fetches NFL data from nfl-data-py (nflverse) and writes to the rankings SQLite database.
Called via CLI command, not on every API request.
"""

import nfl_data_py as nfl
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
    "EDGE": "DEF",
    # Offensive
    "QB": "QB",
    "RB": "RB", "FB": "RB", "HB": "RB",
    "WR": "WR",
    "TE": "TE",
    # Special teams
    "K": "K",
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


def ingest_seasonal_offensive(seasons: list[int]):
    """Fetch seasonal offensive stats (QB, RB, WR, TE) from nflverse."""
    init_rankings_db()
    session = RankingsSessionLocal()
    started = datetime.utcnow()

    try:
        print(f"Fetching seasonal data for {seasons}...")
        seasonal = nfl.import_seasonal_data(seasons, s_type="REG")

        if seasonal.empty:
            print("No seasonal data returned.")
            return 0

        count = 0
        for _, row in seasonal.iterrows():
            player_id = row.get("player_id")
            season = int(row.get("season", 0))
            if not player_id or not season:
                continue

            # Check if player exists in our players table
            player = session.get(Player, player_id)
            if not player:
                continue

            # Skip defensive players and kickers (handled by PBP)
            if player.position_group in ("DEF", "K"):
                continue

            games = int(row.get("games", 0))
            if games == 0:
                continue

            # Upsert stats
            existing = session.query(PlayerSeasonStats).filter_by(
                gsis_id=player_id, season=season
            ).first()

            if not existing:
                existing = PlayerSeasonStats(gsis_id=player_id, season=season)
                session.add(existing)

            existing.games_played = games
            # Passing
            existing.completions = _safe_float(row, "completions")
            existing.attempts = _safe_float(row, "attempts")
            existing.passing_yards = _safe_float(row, "passing_yards")
            existing.passing_tds = _safe_float(row, "passing_tds")
            existing.interceptions = _safe_float(row, "interceptions")
            existing.sacks = _safe_float(row, "sacks")
            existing.sack_yards = _safe_float(row, "sack_yards")
            existing.passing_first_downs = _safe_float(row, "passing_first_downs")
            existing.sack_fumbles = _safe_float(row, "sack_fumbles")
            # Rushing
            existing.carries = _safe_float(row, "carries")
            existing.rushing_yards = _safe_float(row, "rushing_yards")
            existing.rushing_tds = _safe_float(row, "rushing_tds")
            existing.rushing_first_downs = _safe_float(row, "rushing_first_downs")
            existing.rushing_fumbles = _safe_float(row, "rushing_fumbles")
            # Receiving
            existing.receptions = _safe_float(row, "receptions")
            existing.targets = _safe_float(row, "targets")
            existing.receiving_yards = _safe_float(row, "receiving_yards")
            existing.receiving_tds = _safe_float(row, "receiving_tds")
            existing.receiving_fumbles = _safe_float(row, "receiving_fumbles")
            existing.receiving_first_downs = _safe_float(row, "receiving_first_downs")
            existing.receiving_yards_after_catch = _safe_float(row, "receiving_yards_after_catch")

            existing.updated_at = datetime.utcnow()
            count += 1

        session.commit()
        print(f"Ingested seasonal stats for {count} player-seasons.")
        for s in seasons:
            _log_ingestion(session, s, "seasonal", count, "success", started_at=started)
        return count

    except Exception as e:
        session.rollback()
        print(f"Error ingesting seasonal data: {e}")
        for s in seasons:
            _log_ingestion(session, s, "seasonal", 0, "error", str(e), started_at=started)
        raise
    finally:
        session.close()


def ingest_pbp_defense(seasons: list[int]):
    """Aggregate defensive stats from play-by-play data."""
    init_rankings_db()
    session = RankingsSessionLocal()
    started = datetime.utcnow()

    try:
        print(f"Fetching play-by-play data for {seasons} (this may take a minute)...")
        pbp = nfl.import_pbp_data(seasons, downcast=False)

        # Regular season only
        pbp = pbp[pbp["season_type"] == "REG"]
        print(f"Processing {len(pbp)} regular season plays...")

        # Aggregate defensive stats per player
        player_stats = {}  # gsis_id -> {stat: value}
        player_games = {}  # gsis_id -> set of game_ids

        for _, play in pbp.iterrows():
            game_id = play.get("game_id")
            season = int(play.get("season", seasons[0]))
            defteam = play.get("defteam")

            # Solo tackles
            for i in [1, 2]:
                pid = play.get(f"solo_tackle_{i}_player_id")
                if pd.notna(pid):
                    _init_player_stats(player_stats, player_games, pid, season)
                    player_stats[pid]["solo_tackles"] += 1
                    player_stats[pid]["tackles"] += 1
                    if pd.notna(game_id):
                        player_games[pid].add(game_id)

            # Assist tackles
            for i in [1, 2, 3, 4]:
                pid = play.get(f"assist_tackle_{i}_player_id")
                if pd.notna(pid):
                    _init_player_stats(player_stats, player_games, pid, season)
                    player_stats[pid]["assists"] += 1
                    player_stats[pid]["tackles"] += 1
                    if pd.notna(game_id):
                        player_games[pid].add(game_id)

            # Tackle with assist (combined tackles)
            for i in [1, 2]:
                pid = play.get(f"tackle_with_assist_{i}_player_id")
                if pd.notna(pid):
                    _init_player_stats(player_stats, player_games, pid, season)
                    # These are tackles where multiple players share credit
                    player_stats[pid]["assists"] += 1
                    player_stats[pid]["tackles"] += 1
                    if pd.notna(game_id):
                        player_games[pid].add(game_id)

            # Sacks (full sack)
            sack_pid = play.get("sack_player_id")
            if pd.notna(sack_pid):
                _init_player_stats(player_stats, player_games, sack_pid, season)
                player_stats[sack_pid]["def_sacks"] += 1.0
                if pd.notna(game_id):
                    player_games[sack_pid].add(game_id)

            # Half sacks
            for i in [1, 2]:
                pid = play.get(f"half_sack_{i}_player_id")
                if pd.notna(pid):
                    _init_player_stats(player_stats, player_games, pid, season)
                    player_stats[pid]["def_sacks"] += 0.5
                    if pd.notna(game_id):
                        player_games[pid].add(game_id)

            # QB hits
            for i in [1, 2]:
                pid = play.get(f"qb_hit_{i}_player_id")
                if pd.notna(pid):
                    _init_player_stats(player_stats, player_games, pid, season)
                    player_stats[pid]["qb_hits"] += 1
                    if pd.notna(game_id):
                        player_games[pid].add(game_id)

            # Tackles for loss
            for i in [1, 2]:
                pid = play.get(f"tackle_for_loss_{i}_player_id")
                if pd.notna(pid):
                    _init_player_stats(player_stats, player_games, pid, season)
                    player_stats[pid]["tackles_for_loss"] += 1
                    if pd.notna(game_id):
                        player_games[pid].add(game_id)

            # Interceptions
            int_pid = play.get("interception_player_id")
            if pd.notna(int_pid):
                _init_player_stats(player_stats, player_games, int_pid, season)
                player_stats[int_pid]["def_interceptions"] += 1
                if pd.notna(game_id):
                    player_games[int_pid].add(game_id)

            # Passes defended
            for i in [1, 2]:
                pid = play.get(f"pass_defense_{i}_player_id")
                if pd.notna(pid):
                    _init_player_stats(player_stats, player_games, pid, season)
                    player_stats[pid]["passes_defended"] += 1
                    if pd.notna(game_id):
                        player_games[pid].add(game_id)

            # Forced fumbles
            for i in [1, 2]:
                pid = play.get(f"forced_fumble_player_{i}_player_id")
                if pd.notna(pid):
                    _init_player_stats(player_stats, player_games, pid, season)
                    player_stats[pid]["forced_fumbles"] += 1
                    if pd.notna(game_id):
                        player_games[pid].add(game_id)

            # Fumble recoveries (only count if recovered by defensive team)
            fr_pid = play.get("fumble_recovery_1_player_id")
            fr_team = play.get("fumble_recovery_1_team")
            if pd.notna(fr_pid) and pd.notna(fr_team) and fr_team == defteam:
                _init_player_stats(player_stats, player_games, fr_pid, season)
                player_stats[fr_pid]["fumble_recoveries"] += 1
                if pd.notna(game_id):
                    player_games[fr_pid].add(game_id)

            fr_pid2 = play.get("fumble_recovery_2_player_id")
            fr_team2 = play.get("fumble_recovery_2_team")
            if pd.notna(fr_pid2) and pd.notna(fr_team2) and fr_team2 == defteam:
                _init_player_stats(player_stats, player_games, fr_pid2, season)
                player_stats[fr_pid2]["fumble_recoveries"] += 1
                if pd.notna(game_id):
                    player_games[fr_pid2].add(game_id)

            # Defensive TDs (interception/fumble return TDs)
            if play.get("return_touchdown") == 1 or (play.get("touchdown") == 1 and play.get("td_team") == defteam):
                td_pid = play.get("td_player_id")
                td_team = play.get("td_team")
                if pd.notna(td_pid) and pd.notna(td_team) and td_team == defteam:
                    _init_player_stats(player_stats, player_games, td_pid, season)
                    player_stats[td_pid]["defensive_tds"] += 1
                    if pd.notna(game_id):
                        player_games[td_pid].add(game_id)

        # Write to database — only for players in our players table with DEF position_group
        count = 0
        for gsis_id, stats in player_stats.items():
            player = session.get(Player, gsis_id)
            if not player or player.position_group != "DEF":
                continue

            season_val = stats["season"]
            games = len(player_games.get(gsis_id, set()))

            existing = session.query(PlayerSeasonStats).filter_by(
                gsis_id=gsis_id, season=season_val
            ).first()

            if not existing:
                existing = PlayerSeasonStats(gsis_id=gsis_id, season=season_val)
                session.add(existing)

            existing.games_played = games
            existing.tackles = stats["tackles"]
            existing.solo_tackles = stats["solo_tackles"]
            existing.assists = stats["assists"]
            existing.def_sacks = stats["def_sacks"]
            existing.qb_hits = stats["qb_hits"]
            existing.tackles_for_loss = stats["tackles_for_loss"]
            existing.passes_defended = stats["passes_defended"]
            existing.def_interceptions = stats["def_interceptions"]
            existing.forced_fumbles = stats["forced_fumbles"]
            existing.fumble_recoveries = stats["fumble_recoveries"]
            existing.defensive_tds = stats["defensive_tds"]
            existing.updated_at = datetime.utcnow()
            count += 1

        session.commit()
        print(f"Ingested defensive stats for {count} players.")
        for s in seasons:
            _log_ingestion(session, s, "pbp_defense", count, "success", started_at=started)
        return count

    except Exception as e:
        session.rollback()
        print(f"Error ingesting defensive stats: {e}")
        for s in seasons:
            _log_ingestion(session, s, "pbp_defense", 0, "error", str(e), started_at=started)
        raise
    finally:
        session.close()


def ingest_pbp_kicking(seasons: list[int]):
    """Aggregate kicking stats from play-by-play data."""
    init_rankings_db()
    session = RankingsSessionLocal()
    started = datetime.utcnow()

    try:
        print(f"Fetching PBP kicking data for {seasons}...")
        pbp = nfl.import_pbp_data(seasons, downcast=False)
        pbp = pbp[pbp["season_type"] == "REG"]

        # Filter to FG and XP plays
        kick_plays = pbp[
            (pbp["field_goal_attempt"] == 1) | (pbp["extra_point_attempt"] == 1)
        ].copy()

        print(f"Processing {len(kick_plays)} kicking plays...")

        kicker_stats = {}  # gsis_id -> stats dict
        kicker_games = {}  # gsis_id -> set of game_ids

        for _, play in kick_plays.iterrows():
            kicker_id = play.get("kicker_player_id")
            if pd.notna(kicker_id) is False:
                continue

            game_id = play.get("game_id")
            season = int(play.get("season", seasons[0]))

            if kicker_id not in kicker_stats:
                kicker_stats[kicker_id] = {
                    "season": season,
                    "fg_made": 0, "fg_attempts": 0,
                    "fg_made_40_49": 0, "fg_made_50_plus": 0, "long_fg": 0,
                    "xp_made": 0, "xp_attempts": 0,
                }
                kicker_games[kicker_id] = set()

            if pd.notna(game_id):
                kicker_games[kicker_id].add(game_id)

            # Field goals
            if play.get("field_goal_attempt") == 1:
                kicker_stats[kicker_id]["fg_attempts"] += 1
                distance = play.get("kick_distance", 0)
                if pd.isna(distance):
                    distance = 0

                if play.get("field_goal_result") == "made":
                    kicker_stats[kicker_id]["fg_made"] += 1
                    if 40 <= distance <= 49:
                        kicker_stats[kicker_id]["fg_made_40_49"] += 1
                    elif distance >= 50:
                        kicker_stats[kicker_id]["fg_made_50_plus"] += 1
                    if distance > kicker_stats[kicker_id]["long_fg"]:
                        kicker_stats[kicker_id]["long_fg"] = distance

            # Extra points
            if play.get("extra_point_attempt") == 1:
                kicker_stats[kicker_id]["xp_attempts"] += 1
                if play.get("extra_point_result") == "good":
                    kicker_stats[kicker_id]["xp_made"] += 1

        # Write to database
        count = 0
        for gsis_id, stats in kicker_stats.items():
            player = session.get(Player, gsis_id)
            if not player or player.position_group != "K":
                continue

            season_val = stats["season"]
            games = len(kicker_games.get(gsis_id, set()))

            existing = session.query(PlayerSeasonStats).filter_by(
                gsis_id=gsis_id, season=season_val
            ).first()

            if not existing:
                existing = PlayerSeasonStats(gsis_id=gsis_id, season=season_val)
                session.add(existing)

            existing.games_played = games
            existing.fg_made = stats["fg_made"]
            existing.fg_attempts = stats["fg_attempts"]
            existing.fg_made_40_49 = stats["fg_made_40_49"]
            existing.fg_made_50_plus = stats["fg_made_50_plus"]
            existing.long_fg = stats["long_fg"]
            existing.xp_made = stats["xp_made"]
            existing.xp_attempts = stats["xp_attempts"]
            existing.kicking_points = stats["fg_made"] * 3 + stats["xp_made"]
            existing.updated_at = datetime.utcnow()
            count += 1

        session.commit()
        print(f"Ingested kicking stats for {count} kickers.")
        for s in seasons:
            _log_ingestion(session, s, "pbp_kicking", count, "success", started_at=started)
        return count

    except Exception as e:
        session.rollback()
        print(f"Error ingesting kicking stats: {e}")
        for s in seasons:
            _log_ingestion(session, s, "pbp_kicking", 0, "error", str(e), started_at=started)
        raise
    finally:
        session.close()


def refresh_all(season: int):
    """Run full data refresh for a given season."""
    print(f"\n{'='*60}")
    print(f"  SSAT Rankings Data Refresh — Season {season}")
    print(f"{'='*60}\n")

    init_rankings_db()

    print("Step 1/4: Ingesting player roster...")
    ingest_players()

    print(f"\nStep 2/4: Ingesting seasonal offensive stats...")
    ingest_seasonal_offensive([season])

    print(f"\nStep 3/4: Ingesting defensive stats from PBP...")
    ingest_pbp_defense([season])

    print(f"\nStep 4/4: Ingesting kicking stats from PBP...")
    ingest_pbp_kicking([season])

    print(f"\n{'='*60}")
    print(f"  Refresh complete for season {season}!")
    print(f"{'='*60}\n")


# --- Helper functions ---

def _safe_float(row, col, default=0.0):
    """Safely extract a float from a pandas row."""
    val = row.get(col, default)
    if pd.isna(val):
        return default
    return float(val)


def _init_player_stats(player_stats, player_games, pid, season):
    """Initialize a player's stats dict if not already present."""
    if pid not in player_stats:
        player_stats[pid] = {
            "season": season,
            "tackles": 0, "solo_tackles": 0, "assists": 0,
            "def_sacks": 0.0, "qb_hits": 0, "tackles_for_loss": 0,
            "passes_defended": 0, "def_interceptions": 0,
            "forced_fumbles": 0, "fumble_recoveries": 0, "defensive_tds": 0,
        }
        player_games[pid] = set()

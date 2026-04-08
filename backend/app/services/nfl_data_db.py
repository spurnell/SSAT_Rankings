"""
Database-backed NFL data service.

Reads player stats from SQLite and returns DataFrames compatible with the
ranking engine. Replaces the PFR scraping in nfl_data.py.
"""

import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Set
from sqlalchemy import text

from app.core.config import settings
from app.core.ranking import (
    calculate_raw_category_z_scores,
    normalize_scores_to_range,
)
from app.core.position_config import (
    get_position_group,
    get_categories_for_group,
    get_category_weights,
    get_log_scale_stats,
    POSITION_GROUPS,
)
from app.db.database import rankings_engine


# Defensive position mapping (same as original nfl_data.py)
DEFENSIVE_POSITIONS = {
    "DL": ["DT", "NT", "DE"],
    "EDGE": ["OLB", "DE", "EDGE"],
    "LB": ["ILB", "MLB", "LB"],
    "CB": ["CB"],
    "S": ["FS", "SS", "S", "DB"],
}


def map_position(pos: str) -> str:
    """Map a specific defensive position to a position group."""
    if not isinstance(pos, str):
        return "LB"
    pos = pos.upper().strip()
    for group, positions in DEFENSIVE_POSITIONS.items():
        if pos in positions:
            return group
    return pos


def _compute_passer_rating(row) -> float:
    """Compute NFL passer rating from a stats row."""
    att = row.get("pass_attempts", 0)
    if att == 0:
        return 0.0
    comp = row.get("completions", 0)
    yds = row.get("pass_yards", 0)
    td = row.get("pass_tds", 0)
    int_ = row.get("interceptions", 0)

    a = max(0, min(2.375, ((comp / att) - 0.3) * 5))
    b = max(0, min(2.375, ((yds / att) - 3) * 0.25))
    c = max(0, min(2.375, (td / att) * 20))
    d = max(0, min(2.375, 2.375 - ((int_ / att) * 25)))

    return ((a + b + c + d) / 6) * 100


def fetch_stats_for_position_group(
    position_group: str,
    season: int = None,
) -> pd.DataFrame:
    """
    Read stats from SQLite and return a DataFrame with columns
    matching position_config.py stat_columns.
    """
    if season is None:
        season = settings.current_season

    group_config = get_position_group(position_group)

    query = """
        SELECT p.gsis_id AS gsis_id, p.display_name, p.position,
               COALESCE(s.team, p.team) AS team,
               s.id AS stats_id, s.season, s.games_played,
               s.completions, s.attempts, s.passing_yards, s.passing_tds,
               s.interceptions, s.sacks, s.sack_yards, s.passing_first_downs,
               s.sack_fumbles, s.carries, s.rushing_yards, s.rushing_tds,
               s.rushing_first_downs, s.rushing_fumbles, s.longest_rush,
               s.receptions, s.targets, s.receiving_yards, s.receiving_tds,
               s.receiving_fumbles, s.receiving_first_downs,
               s.receiving_yards_after_catch, s.longest_reception,
               s.tackles, s.solo_tackles, s.assists, s.def_sacks,
               s.qb_hits, s.tackles_for_loss, s.passes_defended,
               s.def_interceptions, s.forced_fumbles, s.fumble_recoveries,
               s.defensive_tds,
               s.fg_made, s.fg_attempts, s.fg_made_40_49, s.fg_made_50_plus,
               s.long_fg, s.xp_made, s.xp_attempts, s.kicking_points
        FROM player_season_stats s
        JOIN players p ON p.gsis_id = s.gsis_id
        WHERE s.season = :season
          AND p.position_group = :pos_group
          AND s.games_played > 0
    """
    params = {"season": season, "pos_group": position_group}

    with rankings_engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)

    if df.empty:
        return pd.DataFrame()

    # Rename columns to match what position_config expects
    if position_group == "QB":
        df = _prepare_qb_stats(df)
    elif position_group == "RB":
        df = _prepare_rb_stats(df)
    elif position_group in ("WR", "TE"):
        df = _prepare_receiving_stats(df, position_group)
    elif position_group == "DEF":
        df = _prepare_def_stats(df)
    elif position_group == "K":
        df = _prepare_kicking_stats(df)

    # Ensure player_name column exists (ranking engine expects it)
    if "player_name" not in df.columns and "display_name" in df.columns:
        df["player_name"] = df["display_name"]

    # Ensure player_id column (used for hashing)
    if "player_id" not in df.columns:
        df["player_id"] = df["gsis_id"]

    return df


def _prepare_qb_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Map DB columns to QB stat names expected by position_config."""
    df = df.copy()

    df["pass_attempts"] = df["attempts"]
    df["pass_yards"] = df["passing_yards"]
    df["pass_tds"] = df["passing_tds"]
    # Rename interceptions/sacks to disambiguate from DEF (where these
    # stat names mean the opposite — caught/recorded vs thrown/taken).
    df["interceptions_thrown"] = df["interceptions"]
    df["sacks_taken"] = df["sacks"]
    # sack_yards already named correctly
    df["first_downs"] = df["passing_first_downs"]

    # Derived stats
    df["completion_pct"] = np.where(
        df["pass_attempts"] > 0,
        df["completions"] / df["pass_attempts"] * 100,
        0.0,
    )
    df["yards_per_attempt"] = np.where(
        df["pass_attempts"] > 0,
        df["pass_yards"] / df["pass_attempts"],
        0.0,
    )

    # Passer rating
    df["passer_rating"] = df.apply(
        lambda r: _compute_passer_rating({
            "pass_attempts": r["pass_attempts"],
            "completions": r["completions"],
            "pass_yards": r["pass_yards"],
            "pass_tds": r["pass_tds"],
            "interceptions": r["interceptions_thrown"],
        }),
        axis=1,
    )

    # Fumbles = sack_fumbles + rushing_fumbles
    df["fumbles"] = df["sack_fumbles"].fillna(0) + df["rushing_fumbles"].fillna(0)

    # Inverted metrics (higher = better ball security)
    df["int_rate_inv"] = np.where(
        df["pass_attempts"] > 0,
        100 - (df["interceptions_thrown"] / df["pass_attempts"] * 100),
        100.0,
    )
    df["sack_rate_inv"] = np.where(
        df["pass_attempts"] > 0,
        100 - (df["sacks_taken"] / (df["pass_attempts"] + df["sacks_taken"]) * 100),
        100.0,
    )
    df["fumbles_inv"] = np.where(
        df["games_played"] > 0,
        100 - (df["fumbles"] / df["games_played"] * 10),
        100.0,
    )

    # Filter: minimum 50 pass attempts (exclude backup QBs)
    df = df[df["pass_attempts"] >= 50]

    return df


def _prepare_rb_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Map DB columns to RB stat names."""
    df = df.copy()

    df["rush_attempts"] = df["carries"]
    df["rush_yards"] = df["rushing_yards"]
    df["rush_tds"] = df["rushing_tds"]
    df["first_downs"] = df["rushing_first_downs"]
    df["fumbles"] = df["rushing_fumbles"].fillna(0)
    df["longest_rush"] = df["longest_rush"].fillna(0) if "longest_rush" in df.columns else 0
    df["rec_yards"] = df["receiving_yards"]
    df["rec_tds"] = df["receiving_tds"]
    # receptions, targets already named correctly

    # Derived stats
    df["yards_per_carry"] = np.where(
        df["rush_attempts"] > 0,
        df["rush_yards"] / df["rush_attempts"],
        0.0,
    )
    df["touches"] = df["rush_attempts"] + df["receptions"]
    df["yards_per_touch"] = np.where(
        df["touches"] > 0,
        (df["rush_yards"] + df["rec_yards"]) / df["touches"],
        0.0,
    )
    df["total_tds"] = df["rush_tds"] + df["rec_tds"]
    df["success_rate"] = 50.0  # Placeholder (same as original code)

    # Filter: minimum 20 rush attempts
    df = df[df["rush_attempts"] >= 20]

    return df


def _prepare_receiving_stats(df: pd.DataFrame, position_group: str) -> pd.DataFrame:
    """Map DB columns to WR/TE stat names."""
    df = df.copy()

    df["rec_yards"] = df["receiving_yards"]
    df["rec_tds"] = df["receiving_tds"]
    df["first_downs"] = df["receiving_first_downs"]
    df["fumbles"] = df["receiving_fumbles"].fillna(0)
    df["yards_after_catch"] = df["receiving_yards_after_catch"]
    df["longest_rec"] = df["longest_reception"].fillna(0) if "longest_reception" in df.columns else 0
    # receptions, targets already named correctly

    # Derived stats
    df["catch_rate"] = np.where(
        df["targets"] > 0,
        df["receptions"] / df["targets"] * 100,
        0.0,
    )
    df["yards_per_reception"] = np.where(
        df["receptions"] > 0,
        df["rec_yards"] / df["receptions"],
        0.0,
    )
    df["yards_per_target"] = np.where(
        df["targets"] > 0,
        df["rec_yards"] / df["targets"],
        0.0,
    )

    # Filter: minimum 10 targets
    df = df[df["targets"] >= 10]

    return df


def _prepare_def_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Map DB columns to DEF stat names."""
    df = df.copy()

    # Map def_ prefixed columns to the names position_config expects
    df["sacks"] = df["def_sacks"]
    df["interceptions"] = df["def_interceptions"]
    # tackles, solo_tackles, assists, qb_hits, tackles_for_loss,
    # passes_defended, forced_fumbles, fumble_recoveries, defensive_tds
    # are already named correctly

    # Filter: minimum 1 game
    df = df[df["games_played"] >= 1]

    return df


def _prepare_kicking_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Map DB columns to K stat names."""
    df = df.copy()

    df["total_points"] = df["kicking_points"]

    # Derived stats
    df["fg_pct"] = np.where(
        df["fg_attempts"] > 0,
        df["fg_made"] / df["fg_attempts"] * 100,
        0.0,
    )
    df["xp_pct"] = np.where(
        df["xp_attempts"] > 0,
        df["xp_made"] / df["xp_attempts"] * 100,
        0.0,
    )
    # fg_made, fg_attempts, fg_made_40_49, fg_made_50_plus, long_fg,
    # xp_made, xp_attempts already named correctly

    # Filter: minimum 5 FG attempts
    df = df[df["fg_attempts"] >= 5]

    return df


def get_available_seasons() -> List[int]:
    """Return list of seasons with data, descending."""
    with rankings_engine.connect() as conn:
        result = conn.execute(
            text("SELECT DISTINCT season FROM player_season_stats ORDER BY season DESC")
        )
        return [row[0] for row in result]


def process_player_rankings(
    data: Optional[pd.DataFrame] = None,
    min_games: int = 1,
    position_filter: Optional[str] = None,
    weights: Optional[Dict[str, float]] = None,
    position_group: str = "DEF",
    season: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Process player data and calculate rankings for any position group.

    Same signature as the original nfl_data.py version — drop-in replacement.
    """
    group_config = get_position_group(position_group)
    categories = get_categories_for_group(position_group)
    log_scale_stats = get_log_scale_stats(position_group)

    if data is None:
        data = fetch_stats_for_position_group(position_group, season=season)

    if data.empty:
        return []

    data = data.copy()

    # Filter by minimum games
    if "games_played" in data.columns:
        data = data[data["games_played"] >= min_games]

    # Filter by sub-position (for defensive players)
    if position_filter and position_filter != "All" and position_group == "DEF":
        if "position" in data.columns:
            data = data[data["position"].apply(map_position) == position_filter]

    if data.empty:
        return []

    # Get stat columns from config
    stat_cols = group_config["stat_columns"]

    # Ensure all stat columns exist
    for col in stat_cols:
        if col not in data.columns:
            data[col] = 0.0

    all_stats = data[stat_cols].to_dict("records")

    # Calculate raw z-scores for all categories
    raw_category_scores = calculate_raw_category_z_scores(
        all_stats, categories, log_scale_stats
    )

    # Calculate raw overall z-scores
    category_weights = weights or get_category_weights(position_group)
    num_players = len(all_stats)
    raw_overall_scores = []
    for i in range(num_players):
        raw_overall = sum(
            raw_category_scores[cat["id"]][i] * category_weights.get(cat["id"], 0.25)
            for cat in categories
            if cat["id"] in raw_category_scores
        )
        raw_overall_scores.append(raw_overall)

    # Normalize all scores to 60-100
    normalized_overall = normalize_scores_to_range(raw_overall_scores)
    normalized_category_scores = {
        cat_id: normalize_scores_to_range(scores)
        for cat_id, scores in raw_category_scores.items()
    }

    # Build player records
    rankings = []
    data_rows = list(data.iterrows())
    for i, (idx, row) in enumerate(data_rows):
        player_stats = {col: float(row.get(col, 0.0)) for col in stat_cols}

        category_scores = {
            cat["id"]: normalized_category_scores[cat["id"]][i]
            for cat in categories
            if cat["id"] in normalized_category_scores
        }

        overall = normalized_overall[i]

        player_id = row.get("player_id", row.get("gsis_id", str(idx)))
        try:
            player_id_int = abs(hash(str(player_id))) % 1000000
        except Exception:
            player_id_int = idx + 1

        # Determine display position
        raw_position = row.get("position", position_group)
        if position_group == "DEF":
            display_position = map_position(raw_position)
        else:
            display_position = raw_position

        rankings.append({
            "id": player_id_int,
            "name": row.get("player_name", row.get("display_name", "Unknown")),
            "team": row.get("team", "UNK"),
            "position": display_position,
            "position_group": position_group,
            "games_played": int(row.get("games_played", 0)),
            "overall_score": round(overall, 1),
            "category_scores": {k: round(v, 1) for k, v in category_scores.items()},
            "stats": player_stats,
        })

    rankings.sort(key=lambda x: x["overall_score"], reverse=True)
    return rankings

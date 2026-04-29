"""
PFF Data Service — loads PFF CSV data and produces rankings for all position groups
using the same z-score engine as the standard nflverse pipeline.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.ranking import (
    calculate_raw_category_z_scores,
    normalize_scores_to_range,
)
from app.core.position_config import get_pff_config

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "cache"

# CSV file paths per position group: list of (filename, role)
PFF_CSV_PATHS: Dict[str, List[tuple]] = {
    "QB": [("pff_passing_2025.csv", "primary")],
    "RB": [("pff_rushing_2025.csv", "primary")],
    "WR": [("pff_receiving_2025.csv", "primary")],
    "TE": [
        ("pff_receiving_2025.csv", "primary"),
        ("pff_pass_blocking_2025.csv", "supplementary"),
    ],
    "DEF_FRONT7": [
        ("pff_defense_2025.csv", "primary"),
        ("pff_pass_rush_2025.csv", "supplementary"),
        ("pff_run_defense_2025.csv", "supplementary"),
    ],
    "DEF_SECONDARY": [
        ("pff_defense_2025.csv", "primary"),
        ("pff_coverage_2025.csv", "supplementary"),
        ("pff_run_defense_2025.csv", "supplementary"),
    ],
    # Coverage-only source. Available to LB/CB/S so the custom-builder can
    # surface coverage stats for off-ball linebackers in addition to DBs.
    # Pure coverage CSV — no run-defense or pass-rush stats here.
    "DEF_COVERAGE": [
        ("pff_coverage_2025.csv", "primary"),
    ],
    "K": [
        ("pff_field_goal_2025.csv", "primary"),
        ("pff_kickoff_2025.csv", "supplementary"),
    ],
}

# PFF position codes per site position group
PFF_POSITION_FILTERS: Dict[str, List[str]] = {
    "QB": ["QB"],
    "RB": ["HB", "FB"],
    "WR": ["WR"],
    "TE": ["TE"],
    "DEF_FRONT7": ["DI", "ED", "LB"],
    "DEF_SECONDARY": ["CB", "S"],
    "DEF_COVERAGE": ["LB", "CB", "S"],
    "K": ["K"],
}

# Minimum thresholds per position group
PFF_MIN_THRESHOLDS: Dict[str, Dict] = {
    "QB": {"column": "attempts", "value": 100},
    "RB": {"column": "attempts", "value": 50},
    "WR": {"column": "targets", "value": 30},
    "TE": {"column": "targets", "value": 15},
    "DEF_FRONT7": {"column": "snap_counts_defense", "value": 100},
    "DEF_SECONDARY": {"column": "snap_counts_defense", "value": 100},
    # Coverage CSV uses a coverage-snap counter rather than total defensive snaps.
    "DEF_COVERAGE": {"column": "snap_counts_coverage", "value": 50},
    "K": {"column": "total_attempts", "value": 10},
}

# Map PFF position codes to site position codes for output
PFF_TO_SITE_POSITION: Dict[str, str] = {
    "HB": "RB",
    "FB": "FB",
    "DI": "DL",
    "ED": "EDGE",
}

# Map site sub-position codes to PFF codes for filtering
SITE_TO_PFF_SUBPOSITION: Dict[str, str] = {
    "DL": "DI",
    "EDGE": "ED",
}


def load_pff_data(position_group: str) -> pd.DataFrame:
    """Load and merge PFF CSV data for a position group."""
    csv_paths = PFF_CSV_PATHS.get(position_group)
    if not csv_paths:
        return pd.DataFrame()

    # Load primary CSV
    primary_path = DATA_DIR / csv_paths[0][0]
    if not primary_path.exists():
        return pd.DataFrame()
    df = pd.read_csv(primary_path)

    # Load and left-join supplementary CSVs
    for filename, role in csv_paths[1:]:
        supp_path = DATA_DIR / filename
        if not supp_path.exists():
            continue
        supp_df = pd.read_csv(supp_path)

        # Only keep columns unique to the supplementary file (plus player_id for join)
        existing_cols = set(df.columns)
        new_cols = [c for c in supp_df.columns if c not in existing_cols or c == "player_id"]
        if "player_id" in new_cols and len(new_cols) > 1:
            supp_df = supp_df[new_cols]
            df = df.merge(supp_df, on="player_id", how="left")

    # Filter by position
    position_filter = PFF_POSITION_FILTERS.get(position_group, [])
    if position_filter and "position" in df.columns:
        df = df[df["position"].isin(position_filter)]

    # Apply minimum threshold
    threshold = PFF_MIN_THRESHOLDS.get(position_group)
    if threshold and threshold["column"] in df.columns:
        df = df[df[threshold["column"]] >= threshold["value"]]

    return df.reset_index(drop=True)


def _prepare_pff_qb_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute inverted stats for QB and merge in PFF rushing data for mobile QBs."""
    df = df.copy()
    df["drop_rate_inv"] = 100 - df["drop_rate"].fillna(0)
    df["twp_rate_inv"] = 100 - df["twp_rate"].fillna(0)
    df["interceptions_inv"] = df["interceptions"].max() - df["interceptions"].fillna(0)
    df["pressure_to_sack_rate_inv"] = 100 - df["pressure_to_sack_rate"].fillna(0)
    df["sack_percent_inv"] = 100 - df["sack_percent"].fillna(0)
    df["fumbles_inv"] = np.where(
        df["player_game_count"] > 0,
        100 - (df["grades_hands_fumble"].fillna(0) / df["player_game_count"] * 10),
        100.0,
    )

    # Merge in QB rows from the PFF rushing CSV. Renaming up front so the
    # rushing-side columns don't collide with passing-CSV columns of the same
    # name (yards, touchdowns, first_downs, attempts, ypa).
    rushing_path = DATA_DIR / "pff_rushing_2025.csv"
    rush_cols = [
        "rush_yards", "rush_tds", "rush_ypa", "rush_yco_attempt",
        "rush_elusive_rating", "rush_first_downs", "rush_attempts",
        "rush_breakaway_percent",
    ]
    if rushing_path.exists():
        rdf = pd.read_csv(rushing_path)
        if "position" in rdf.columns:
            rdf = rdf[rdf["position"] == "QB"]
        rename_map = {
            "yards": "rush_yards",
            "touchdowns": "rush_tds",
            "ypa": "rush_ypa",
            "yco_attempt": "rush_yco_attempt",
            "elusive_rating": "rush_elusive_rating",
            "first_downs": "rush_first_downs",
            "attempts": "rush_attempts",
            "breakaway_percent": "rush_breakaway_percent",
        }
        keep = ["player_id"] + [src for src in rename_map if src in rdf.columns]
        rdf = rdf[keep].rename(columns=rename_map)
        df = df.merge(rdf, on="player_id", how="left")

    # Pure pocket QBs may have no rushing row — fill those with 0 so they
    # score low (correct) in the rushing category rather than dropping out.
    for col in rush_cols:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = df[col].fillna(0.0)

    return df


def _prepare_pff_rb_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute inverted stats for RB."""
    df = df.copy()
    df["fumbles_inv"] = df["fumbles"].max() - df["fumbles"].fillna(0)
    return df


def _prepare_pff_wr_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute inverted stats for WR."""
    df = df.copy()
    df["drop_rate_inv"] = 100 - df["drop_rate"].fillna(0)
    return df


def _prepare_pff_te_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute inverted stats for TE."""
    df = df.copy()
    df["drop_rate_inv"] = 100 - df["drop_rate"].fillna(0)
    # Fill missing blocking data with 0 (TEs without blocking snaps)
    for col in ["grades_pass_block", "pass_block_percent", "pressures_allowed"]:
        if col not in df.columns:
            df[col] = 0.0
    df["pressures_allowed"] = df["pressures_allowed"].fillna(0)
    max_pa = df["pressures_allowed"].max()
    df["pressures_allowed_inv"] = max_pa - df["pressures_allowed"] if max_pa > 0 else 0.0
    return df


def _prepare_pff_def_front7_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute inverted stats for DEF Front 7."""
    df = df.copy()
    df["missed_tackle_rate"] = df["missed_tackle_rate"].fillna(0)
    df["missed_tackle_rate_inv"] = 100 - df["missed_tackle_rate"]
    return df


def _prepare_pff_coverage_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute inverted stats for the coverage-only source (LB/CB/S).

    Mirrors the inversions used by DEF_SECONDARY but operates on the pure
    pff_coverage_2025.csv (no defense/run-defense merge), so the column set
    is what's surfaced to the bubble grid for LB/CB/S.
    """
    df = df.copy()
    df["missed_tackle_rate"] = df["missed_tackle_rate"].fillna(0)
    df["missed_tackle_rate_inv"] = 100 - df["missed_tackle_rate"]
    df["qb_rating_against"] = df["qb_rating_against"].fillna(0)
    max_qbr = df["qb_rating_against"].max()
    df["qb_rating_against_inv"] = (
        max_qbr - df["qb_rating_against"] if max_qbr > 0 else 0.0
    )
    df["catch_rate"] = df["catch_rate"].fillna(0)
    max_cr = df["catch_rate"].max()
    df["catch_rate_inv"] = max_cr - df["catch_rate"] if max_cr > 0 else 0.0
    df["yards_per_coverage_snap"] = df["yards_per_coverage_snap"].fillna(0)
    max_ypcs = df["yards_per_coverage_snap"].max()
    df["yards_per_coverage_snap_inv"] = (
        max_ypcs - df["yards_per_coverage_snap"] if max_ypcs > 0 else 0.0
    )
    return df


def _prepare_pff_def_secondary_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute inverted stats for DEF Secondary."""
    df = df.copy()
    df["missed_tackle_rate"] = df["missed_tackle_rate"].fillna(0)
    df["missed_tackle_rate_inv"] = 100 - df["missed_tackle_rate"]
    df["qb_rating_against"] = df["qb_rating_against"].fillna(0)
    max_qbr = df["qb_rating_against"].max()
    df["qb_rating_against_inv"] = max_qbr - df["qb_rating_against"] if max_qbr > 0 else 0.0
    df["catch_rate"] = df["catch_rate"].fillna(0)
    max_cr = df["catch_rate"].max()
    df["catch_rate_inv"] = max_cr - df["catch_rate"] if max_cr > 0 else 0.0
    df["yards_per_coverage_snap"] = df["yards_per_coverage_snap"].fillna(0) if "yards_per_coverage_snap" in df.columns else 0.0
    if "yards_per_coverage_snap" in df.columns:
        max_ypcs = df["yards_per_coverage_snap"].max()
        df["yards_per_coverage_snap_inv"] = max_ypcs - df["yards_per_coverage_snap"] if max_ypcs > 0 else 0.0
    else:
        df["yards_per_coverage_snap_inv"] = 0.0
    return df


def _prepare_pff_k_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute inverted stats for K."""
    df = df.copy()
    # Fill missing kickoff data
    for col in ["grades_kickoff_kicker", "touchbacks", "average_yards_per_return"]:
        if col not in df.columns:
            df[col] = 0.0
    df["average_yards_per_return"] = df["average_yards_per_return"].fillna(0)
    max_ypr = df["average_yards_per_return"].max()
    df["average_yards_per_return_inv"] = max_ypr - df["average_yards_per_return"] if max_ypr > 0 else 0.0
    # Fill NaN percentages with 0 (kickers who didn't attempt from certain ranges)
    for col in ["fifty_percent", "forty_percent", "thirty_percent", "twenty_percent", "pat_percent", "total_percent"]:
        if col in df.columns:
            df[col] = df[col].fillna(0)
    return df


# Map position group to its prep function
_PREPARE_FUNCTIONS = {
    "QB": _prepare_pff_qb_stats,
    "RB": _prepare_pff_rb_stats,
    "WR": _prepare_pff_wr_stats,
    "TE": _prepare_pff_te_stats,
    "DEF_FRONT7": _prepare_pff_def_front7_stats,
    "DEF_SECONDARY": _prepare_pff_def_secondary_stats,
    "DEF_COVERAGE": _prepare_pff_coverage_stats,
    "K": _prepare_pff_k_stats,
}


PFF_DATA_SEASON = 2025


def process_pff_rankings(
    position_group: str,
    min_games: int = 1,
    weights: Optional[Dict[str, float]] = None,
    position_filter: Optional[str] = None,
    source: str = "pff",
    season: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Generic PFF ranking processor for any position group.
    Returns rankings in the same format as process_player_rankings.

    For DEF, pass position_group="DEF_FRONT7" or "DEF_SECONDARY"
    (or pass position_group="DEF" with source="pff_front7"/"pff_secondary").

    PFF data is currently only available for the 2025 season — requests for any
    other season return an empty list.
    """
    # Refuse non-2025 season requests (PFF CSVs are 2025-only)
    if season is not None and season != PFF_DATA_SEASON:
        return []

    # Map source-based DEF requests to internal group keys
    internal_group = position_group
    if position_group == "DEF" and source in ("pff_front7", "pff_secondary", "pff_coverage"):
        internal_group = {
            "pff_front7": "DEF_FRONT7",
            "pff_secondary": "DEF_SECONDARY",
            "pff_coverage": "DEF_COVERAGE",
        }[source]

    config = get_pff_config(position_group, source=source)
    if not config:
        return []

    categories = config["categories"]
    stat_cols = config["stat_columns"]
    # When weights were supplied explicitly (saved ranking), fall back to 0
    # for missing category ids; only the config-defaults path uses 0.20.
    explicit_weights = weights is not None
    category_weights = weights if explicit_weights else config["weights"]
    default_weight = 0.0 if explicit_weights else 0.20

    df = load_pff_data(internal_group)
    if df.empty:
        return []

    # Apply position-specific stat prep
    prep_fn = _PREPARE_FUNCTIONS.get(internal_group)
    if prep_fn:
        df = prep_fn(df)

    # Standardize column names
    if "player" in df.columns:
        df["player_name"] = df["player"]
    if "team_name" in df.columns:
        df["team"] = df["team_name"]
    if "player_game_count" in df.columns:
        df["games_played"] = df["player_game_count"]

    # Apply min games filter
    if min_games > 1 and "games_played" in df.columns:
        df = df[df["games_played"] >= min_games]

    # Apply sub-position filter (for DEF)
    if position_filter and position_filter != "All" and "position" in df.columns:
        pff_code = SITE_TO_PFF_SUBPOSITION.get(position_filter, position_filter)
        df = df[df["position"] == pff_code]

    if df.empty:
        return []

    # Ensure all stat columns exist
    for col in stat_cols:
        if col not in df.columns:
            df[col] = 0.0

    # Fill NaN in stat columns
    df[stat_cols] = df[stat_cols].fillna(0)

    all_stats = df[stat_cols].to_dict("records")

    # Reuse existing ranking engine
    raw_category_scores = calculate_raw_category_z_scores(
        all_stats, categories, set()
    )

    # Calculate raw overall z-scores
    num_players = len(all_stats)
    raw_overall_scores = []
    for i in range(num_players):
        raw_overall = sum(
            raw_category_scores[cat["id"]][i] * category_weights.get(cat["id"], default_weight)
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
    data_rows = list(df.iterrows())
    for i, (idx, row) in enumerate(data_rows):
        player_stats = {col: float(row.get(col, 0.0)) for col in stat_cols}

        category_scores = {
            cat["id"]: normalized_category_scores[cat["id"]][i]
            for cat in categories
            if cat["id"] in normalized_category_scores
        }

        player_id = row.get("player_id", idx)
        try:
            player_id_int = abs(hash(str(player_id))) % 1000000
        except Exception:
            player_id_int = idx + 1

        # Map PFF position code to site code
        pff_position = row.get("position", "")
        site_position = PFF_TO_SITE_POSITION.get(pff_position, pff_position)

        rankings.append({
            "id": player_id_int,
            "name": row.get("player_name", "Unknown"),
            "team": row.get("team", "UNK"),
            "position": site_position,
            "position_group": position_group,
            "games_played": int(row.get("games_played", 0)),
            "overall_score": round(normalized_overall[i], 1),
            "category_scores": {k: round(v, 1) for k, v in category_scores.items()},
            "stats": player_stats,
        })

    rankings.sort(key=lambda x: x["overall_score"], reverse=True)
    return rankings


# Backward-compatible wrapper
def process_pff_qb_rankings(
    min_games: int = 1,
    weights: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """Process PFF QB rankings (backward-compatible wrapper)."""
    return process_pff_rankings("QB", min_games=min_games, weights=weights)

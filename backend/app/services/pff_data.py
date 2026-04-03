"""
PFF Data Service — loads PFF passing CSV and produces QB rankings
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
from app.core.position_config import get_pff_qb_config

PFF_CSV_PATH = Path(__file__).parent.parent.parent / "data" / "cache" / "pff_passing_2025.csv"

MIN_ATTEMPTS = 100


def load_pff_passing_data() -> pd.DataFrame:
    """Load and filter PFF passing data from CSV."""
    df = pd.read_csv(PFF_CSV_PATH)

    # Filter: only QBs with minimum attempts
    df = df[df["position"] == "QB"]
    df = df[df["attempts"] >= MIN_ATTEMPTS]

    return df.reset_index(drop=True)


def _prepare_pff_qb_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute inverted stats so higher is always better for the z-score engine."""
    df = df.copy()

    # Inverted stats (higher = better)
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

    # Rename columns for consistency with our config
    df["player_name"] = df["player"]
    df["team"] = df["team_name"]
    df["games_played"] = df["player_game_count"]

    return df


def process_pff_qb_rankings(
    min_games: int = 1,
    weights: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """
    Process PFF QB data and return rankings in the same format
    as process_player_rankings from nfl_data_db.
    """
    config = get_pff_qb_config()
    categories = config["categories"]
    stat_cols = config["stat_columns"]
    category_weights = weights or config["weights"]

    df = load_pff_passing_data()
    df = _prepare_pff_qb_stats(df)

    if min_games > 1:
        df = df[df["games_played"] >= min_games]

    if df.empty:
        return []

    # Ensure all stat columns exist
    for col in stat_cols:
        if col not in df.columns:
            df[col] = 0.0

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
            raw_category_scores[cat["id"]][i] * category_weights.get(cat["id"], 0.20)
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

    # Build player records (same shape as process_player_rankings)
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

        rankings.append({
            "id": player_id_int,
            "name": row.get("player_name", "Unknown"),
            "team": row.get("team", "UNK"),
            "position": "QB",
            "position_group": "QB",
            "games_played": int(row.get("games_played", 0)),
            "overall_score": round(normalized_overall[i], 1),
            "category_scores": {k: round(v, 1) for k, v in category_scores.items()},
            "stats": player_stats,
        })

    rankings.sort(key=lambda x: x["overall_score"], reverse=True)
    return rankings

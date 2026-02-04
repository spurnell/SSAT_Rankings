import numpy as np
from typing import Dict, List, Optional, Set

from app.core.position_config import (
    CategoryConfig,
    get_categories_for_group,
    get_log_scale_stats,
    get_category_weights,
    # Backward compatibility exports
    CATEGORY_STATS,
    PLAYMAKING_STATS,
)


def log_scale_z_score(z: float) -> float:
    """Log-scale z-score to compress extremes: sign(z) * log(1 + |z|)."""
    return float(np.sign(z) * np.log1p(abs(z)))


def calculate_z_score(value: float, mean: float, std: float) -> float:
    """Calculate z-score for a single value."""
    if std == 0:
        return 0.0
    return (value - mean) / std


def calculate_z_scores(values: List[float]) -> List[float]:
    """Calculate z-scores for a list of values."""
    if not values:
        return []
    arr = np.array(values)
    mean = np.mean(arr)
    std = np.std(arr)
    if std == 0:
        return [0.0] * len(values)
    return ((arr - mean) / std).tolist()


def aggregate_z_scores(
    z_scores: List[float], weights: Optional[List[float]] = None
) -> float:
    """
    Aggregate multiple z-scores into a single composite score.
    Uses equal weighting if no weights provided.
    """
    if not z_scores:
        return 0.0
    if weights is None:
        weights = [1.0 / len(z_scores)] * len(z_scores)
    if len(weights) != len(z_scores):
        raise ValueError("Weights must have same length as z_scores")
    return sum(z * w for z, w in zip(z_scores, weights))


def rescale_to_range(
    z_score: float,
    min_score: float = 60.0,
    max_score: float = 100.0,
    z_range: float = 5.0,
) -> float:
    """
    Rescale a z-score to a target range (default 60-100).

    A z-score of 0 maps to the midpoint (80).
    Z-scores are clamped to [-z_range, +z_range] before scaling.

    Note: This is kept for fallback but the primary method is now
    normalize_scores_to_range() which uses min-max normalization.
    """
    clamped = max(-z_range, min(z_range, z_score))
    midpoint = (min_score + max_score) / 2
    half_range = (max_score - min_score) / 2
    return midpoint + (clamped / z_range) * half_range


def normalize_scores_to_range(
    scores: List[float],
    min_score: float = 60.0,
    max_score: float = 100.0,
) -> List[float]:
    """
    Min-max normalize scores so max->100, min->60.

    This ensures the best player gets exactly 100 and the worst gets exactly 60,
    with all others interpolated linearly between.
    """
    if not scores:
        return []
    min_val = min(scores)
    max_val = max(scores)
    if max_val == min_val:
        return [(min_score + max_score) / 2] * len(scores)
    return [
        min_score + (s - min_val) / (max_val - min_val) * (max_score - min_score)
        for s in scores
    ]


def calculate_raw_category_z_scores(
    all_player_stats: List[Dict[str, float]],
    categories: Optional[List[CategoryConfig]] = None,
    log_scale_stats: Optional[Set[str]] = None,
) -> Dict[str, List[float]]:
    """
    Calculate raw (unscaled) composite z-scores for all players.

    Args:
        all_player_stats: List of stat dicts for all players
        categories: List of category configs (uses DEF defaults if None)
        log_scale_stats: Set of stat names that should use log scaling

    Returns:
        Dict mapping category ID to list of z-scores (one per player).
        These are raw z-scores that have not been scaled to 60-100.
    """
    # Default to defensive categories for backward compatibility
    if categories is None:
        from app.core.position_config import DEF_CATEGORIES
        categories = DEF_CATEGORIES

    if log_scale_stats is None:
        log_scale_stats = PLAYMAKING_STATS

    if not all_player_stats:
        return {cat["id"]: [] for cat in categories}

    # Collect all unique stats from categories
    all_stats: Set[str] = set()
    for cat in categories:
        all_stats.update(cat["stats"])

    # Pre-compute z-scores for each stat across all players
    stat_z_scores: Dict[str, List[float]] = {}
    for stat_name in all_stats:
        values = [p.get(stat_name, 0.0) for p in all_player_stats]
        stat_z_scores[stat_name] = calculate_z_scores(values)

    # Calculate composite z-score for each category for each player
    result: Dict[str, List[float]] = {}
    num_players = len(all_player_stats)

    for category in categories:
        category_scores = []
        stat_names = category["stats"]
        cat_log_stats = set(category.get("log_scale_stats", []))

        for player_idx in range(num_players):
            player_stat_z = []
            for stat in stat_names:
                if stat not in stat_z_scores:
                    # Stat not available, use 0
                    z = 0.0
                else:
                    z = stat_z_scores[stat][player_idx]
                # Apply log scaling to stats marked for it
                if stat in cat_log_stats or stat in log_scale_stats:
                    z = log_scale_z_score(z)
                player_stat_z.append(z)
            composite = aggregate_z_scores(player_stat_z)
            category_scores.append(composite)
        result[category["id"]] = category_scores

    return result


def calculate_category_scores_for_group(
    all_player_stats: List[Dict[str, float]],
    position_group: str,
) -> Dict[str, List[float]]:
    """
    Calculate category scores for a specific position group.

    Args:
        all_player_stats: List of stat dicts for all players
        position_group: Position group ID (e.g., 'QB', 'RB', 'DEF')

    Returns:
        Dict mapping category ID to list of normalized scores (60-100 scale).
    """
    categories = get_categories_for_group(position_group)
    log_stats = get_log_scale_stats(position_group)

    # Get raw z-scores
    raw_scores = calculate_raw_category_z_scores(
        all_player_stats, categories, log_stats
    )

    # Normalize each category to 60-100
    normalized = {
        cat_id: normalize_scores_to_range(scores)
        for cat_id, scores in raw_scores.items()
    }

    return normalized


def calculate_overall_scores_for_group(
    raw_category_scores: Dict[str, List[float]],
    position_group: str,
) -> List[float]:
    """
    Calculate overall scores from raw category z-scores for a position group.

    Args:
        raw_category_scores: Dict of category ID to list of raw z-scores
        position_group: Position group ID

    Returns:
        List of raw overall z-scores (one per player)
    """
    weights = get_category_weights(position_group)
    categories = get_categories_for_group(position_group)

    if not raw_category_scores:
        return []

    # Get number of players from first category
    first_cat = categories[0]["id"]
    if first_cat not in raw_category_scores:
        return []

    num_players = len(raw_category_scores[first_cat])

    raw_overall_scores = []
    for i in range(num_players):
        raw_overall = sum(
            raw_category_scores[cat["id"]][i] * weights.get(cat["id"], 0.25)
            for cat in categories
            if cat["id"] in raw_category_scores
        )
        raw_overall_scores.append(raw_overall)

    return raw_overall_scores


# Legacy function for backward compatibility
def calculate_category_scores(
    stats: Dict[str, float],
    all_player_stats: List[Dict[str, float]],
) -> Dict[str, float]:
    """
    Calculate z-scores for each category based on player stats.

    Legacy function for backward compatibility with defensive rankings.

    Categories and their component stats:
    - Run Defense: tackles, solo_tackles, assists, tackles_for_loss
    - Pass Rush: sacks, qb_hits, tackles_for_loss
    - Coverage: passes_defended, interceptions
    - Playmaking: forced_fumbles, fumble_recoveries, interceptions, defensive_tds
    """

    def get_stat_z_score(stat_name: str) -> float:
        values = [p.get(stat_name, 0.0) for p in all_player_stats]
        player_value = stats.get(stat_name, 0.0)
        if not values:
            return 0.0
        mean = np.mean(values)
        std = np.std(values)
        return calculate_z_score(player_value, mean, std)

    # Run Defense: tackles, solo_tackles, assists, tackles_for_loss
    run_def_z = aggregate_z_scores([
        get_stat_z_score("tackles"),
        get_stat_z_score("solo_tackles"),
        get_stat_z_score("assists"),
        get_stat_z_score("tackles_for_loss"),
    ])

    # Pass Rush: sacks, qb_hits, tackles_for_loss
    pass_rush_z = aggregate_z_scores([
        get_stat_z_score("sacks"),
        get_stat_z_score("qb_hits"),
        get_stat_z_score("tackles_for_loss"),
    ])

    # Coverage: passes_defended, interceptions
    coverage_z = aggregate_z_scores([
        get_stat_z_score("passes_defended"),
        get_stat_z_score("interceptions"),
    ])

    # Playmaking: forced_fumbles, fumble_recoveries, interceptions, defensive_tds
    # Apply log scaling to compress extreme z-scores from rare-event stats
    playmaking_z = aggregate_z_scores([
        log_scale_z_score(get_stat_z_score("forced_fumbles")),
        log_scale_z_score(get_stat_z_score("fumble_recoveries")),
        log_scale_z_score(get_stat_z_score("interceptions")),
        log_scale_z_score(get_stat_z_score("defensive_tds")),
    ])

    return {
        "run_defense": rescale_to_range(run_def_z),
        "pass_rush": rescale_to_range(pass_rush_z),
        "coverage": rescale_to_range(coverage_z),
        "playmaking": rescale_to_range(playmaking_z),
    }


def calculate_overall_score(
    category_scores: Dict[str, float],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Calculate overall score from category scores using weights.
    Default weights: equal (0.25 each for defensive categories).
    """
    if weights is None:
        weights = {
            "run_defense": 0.25,
            "pass_rush": 0.25,
            "coverage": 0.25,
            "playmaking": 0.25,
        }

    total = 0.0
    for cat_id, score in category_scores.items():
        total += score * weights.get(cat_id, 0.25)

    return total

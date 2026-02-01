import numpy as np
from typing import TypedDict, Dict, List, Optional


class CategoryScores(TypedDict):
    run_defense: float
    pass_rush: float
    coverage: float
    playmaking: float


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
    z_range: float = 3.0,
) -> float:
    """
    Rescale a z-score to a target range (default 60-100).

    A z-score of 0 maps to the midpoint (80).
    Z-scores are clamped to [-z_range, +z_range] before scaling.
    """
    clamped = max(-z_range, min(z_range, z_score))
    midpoint = (min_score + max_score) / 2
    half_range = (max_score - min_score) / 2
    return midpoint + (clamped / z_range) * half_range


def calculate_category_scores(
    stats: Dict[str, float],
    all_player_stats: List[Dict[str, float]],
) -> CategoryScores:
    """
    Calculate z-scores for each category based on player stats.

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
    playmaking_z = aggregate_z_scores([
        get_stat_z_score("forced_fumbles"),
        get_stat_z_score("fumble_recoveries"),
        get_stat_z_score("interceptions"),
        get_stat_z_score("defensive_tds"),
    ])

    return {
        "run_defense": rescale_to_range(run_def_z),
        "pass_rush": rescale_to_range(pass_rush_z),
        "coverage": rescale_to_range(coverage_z),
        "playmaking": rescale_to_range(playmaking_z),
    }


def calculate_overall_score(
    category_scores: CategoryScores,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Calculate overall score from category scores using weights.
    Default weights: equal (0.25 each).
    """
    if weights is None:
        weights = {
            "run_defense": 0.25,
            "pass_rush": 0.25,
            "coverage": 0.25,
            "playmaking": 0.25,
        }

    total = sum(
        category_scores[cat] * weights.get(cat, 0.25)
        for cat in ["run_defense", "pass_rush", "coverage", "playmaking"]
    )
    return total

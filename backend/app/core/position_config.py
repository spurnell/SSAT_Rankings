"""
Position Configuration - Single source of truth for all NFL position groups.

This module defines all position groups, their categories, stats, and weights.
The ranking engine and frontend read from this config rather than hardcoding values.
"""

from typing import Dict, List, TypedDict, Set


class StatConfig(TypedDict):
    """Configuration for a single stat."""
    name: str
    display_name: str
    higher_is_better: bool  # Whether higher values are better (True for most stats)


class CategoryConfig(TypedDict):
    """Configuration for a ranking category."""
    id: str
    name: str
    stats: List[str]
    weight: float
    log_scale_stats: List[str]  # Stats that need log scaling (rare events)


class PositionGroupConfig(TypedDict, total=False):
    """Configuration for a position group."""
    id: str
    name: str
    data_source: str  # 'defense', 'passing', 'rushing', 'receiving', 'kicking'
    positions: List[str]  # List of position codes included in this group
    categories: List[CategoryConfig]
    stat_columns: List[str]  # All stats used by this position group
    sub_positions: List[str]  # Optional sub-position filters for UI


# Defensive position config (existing)
DEF_CATEGORIES: List[CategoryConfig] = [
    {
        "id": "run_defense",
        "name": "Run Defense",
        "stats": ["tackles", "solo_tackles", "assists", "tackles_for_loss"],
        "weight": 0.25,
        "log_scale_stats": [],
    },
    {
        "id": "pass_rush",
        "name": "Pass Rush",
        "stats": ["sacks", "qb_hits", "tackles_for_loss"],
        "weight": 0.25,
        "log_scale_stats": [],
    },
    {
        "id": "coverage",
        "name": "Coverage",
        "stats": ["passes_defended", "interceptions"],
        "weight": 0.25,
        "log_scale_stats": [],
    },
    {
        "id": "playmaking",
        "name": "Playmaking",
        "stats": ["forced_fumbles", "fumble_recoveries", "interceptions", "defensive_tds"],
        "weight": 0.25,
        "log_scale_stats": ["forced_fumbles", "fumble_recoveries", "interceptions", "defensive_tds"],
    },
]

# Quarterback config
QB_CATEGORIES: List[CategoryConfig] = [
    {
        "id": "efficiency",
        "name": "Efficiency",
        "stats": ["completion_pct", "yards_per_attempt", "passer_rating"],
        "weight": 0.30,
        "log_scale_stats": [],
    },
    {
        "id": "volume",
        "name": "Volume",
        "stats": ["pass_yards", "completions", "pass_attempts"],
        "weight": 0.20,
        "log_scale_stats": [],
    },
    {
        "id": "playmaking",
        "name": "Playmaking",
        "stats": ["pass_tds", "yards_per_attempt", "first_downs"],
        "weight": 0.30,
        "log_scale_stats": [],
    },
    {
        "id": "ball_security",
        "name": "Ball Security",
        "stats": ["int_rate_inv", "sack_rate_inv", "fumbles_inv"],  # _inv = inverted (lower is better)
        "weight": 0.20,
        "log_scale_stats": [],
    },
]

# Running back config
RB_CATEGORIES: List[CategoryConfig] = [
    {
        "id": "efficiency",
        "name": "Efficiency",
        "stats": ["yards_per_carry", "yards_per_touch", "success_rate"],
        "weight": 0.30,
        "log_scale_stats": [],
    },
    {
        "id": "volume",
        "name": "Volume",
        "stats": ["rush_yards", "rush_attempts", "touches"],
        "weight": 0.25,
        "log_scale_stats": [],
    },
    {
        "id": "scoring",
        "name": "Scoring",
        "stats": ["rush_tds", "total_tds"],
        "weight": 0.20,
        "log_scale_stats": ["rush_tds", "total_tds"],
    },
    {
        "id": "receiving",
        "name": "Receiving",
        "stats": ["receptions", "rec_yards", "rec_tds"],
        "weight": 0.25,
        "log_scale_stats": ["rec_tds"],
    },
]

# Wide receiver config
WR_CATEGORIES: List[CategoryConfig] = [
    {
        "id": "efficiency",
        "name": "Efficiency",
        "stats": ["yards_per_reception", "yards_per_target", "catch_rate"],
        "weight": 0.25,
        "log_scale_stats": [],
    },
    {
        "id": "volume",
        "name": "Volume",
        "stats": ["rec_yards", "receptions", "targets"],
        "weight": 0.30,
        "log_scale_stats": [],
    },
    {
        "id": "scoring",
        "name": "Scoring",
        "stats": ["rec_tds", "first_downs"],
        "weight": 0.25,
        "log_scale_stats": ["rec_tds"],
    },
    {
        "id": "playmaking",
        "name": "Playmaking",
        "stats": ["yards_after_catch", "longest_rec", "yards_per_reception"],
        "weight": 0.20,
        "log_scale_stats": [],
    },
]

# Tight end config
TE_CATEGORIES: List[CategoryConfig] = [
    {
        "id": "receiving",
        "name": "Receiving",
        "stats": ["rec_yards", "receptions", "targets"],
        "weight": 0.35,
        "log_scale_stats": [],
    },
    {
        "id": "efficiency",
        "name": "Efficiency",
        "stats": ["yards_per_reception", "catch_rate", "yards_per_target"],
        "weight": 0.30,
        "log_scale_stats": [],
    },
    {
        "id": "scoring",
        "name": "Scoring",
        "stats": ["rec_tds", "first_downs"],
        "weight": 0.35,
        "log_scale_stats": ["rec_tds"],
    },
]

# Kicker config
K_CATEGORIES: List[CategoryConfig] = [
    {
        "id": "accuracy",
        "name": "Accuracy",
        "stats": ["fg_pct", "xp_pct"],
        "weight": 0.40,
        "log_scale_stats": [],
    },
    {
        "id": "volume",
        "name": "Volume",
        "stats": ["fg_made", "xp_made", "total_points"],
        "weight": 0.30,
        "log_scale_stats": [],
    },
    {
        "id": "clutch",
        "name": "Clutch",
        "stats": ["fg_made_40_49", "fg_made_50_plus", "long_fg"],
        "weight": 0.30,
        "log_scale_stats": [],
    },
]


def get_all_stats_for_category(categories: List[CategoryConfig]) -> List[str]:
    """Get all unique stats used by a list of categories."""
    stats: Set[str] = set()
    for cat in categories:
        stats.update(cat["stats"])
    return sorted(list(stats))


# Position group definitions
POSITION_GROUPS: Dict[str, PositionGroupConfig] = {
    "DEF": {
        "id": "DEF",
        "name": "Defensive Players",
        "data_source": "defense",
        "positions": ["DL", "DE", "DT", "NT", "EDGE", "OLB", "ILB", "MLB", "LB", "CB", "FS", "SS", "S", "DB"],
        "categories": DEF_CATEGORIES,
        "stat_columns": [
            "tackles", "solo_tackles", "assists", "sacks", "qb_hits",
            "tackles_for_loss", "passes_defended", "interceptions",
            "forced_fumbles", "fumble_recoveries", "defensive_tds"
        ],
        "sub_positions": ["All", "DL", "EDGE", "LB", "CB", "S"],
    },
    "QB": {
        "id": "QB",
        "name": "Quarterbacks",
        "data_source": "passing",
        "positions": ["QB"],
        "categories": QB_CATEGORIES,
        "stat_columns": [
            "pass_attempts", "completions", "completion_pct", "pass_yards",
            "pass_tds", "interceptions", "passer_rating", "yards_per_attempt",
            "sacks", "sack_yards", "first_downs", "fumbles",
            "int_rate_inv", "sack_rate_inv", "fumbles_inv"
        ],
    },
    "RB": {
        "id": "RB",
        "name": "Running Backs",
        "data_source": "rushing",
        "positions": ["RB", "FB"],
        "categories": RB_CATEGORIES,
        "stat_columns": [
            "rush_attempts", "rush_yards", "yards_per_carry", "rush_tds",
            "first_downs", "longest_rush", "fumbles",
            "receptions", "rec_yards", "rec_tds", "targets",
            "touches", "yards_per_touch", "total_tds", "success_rate"
        ],
    },
    "WR": {
        "id": "WR",
        "name": "Wide Receivers",
        "data_source": "receiving",
        "positions": ["WR"],
        "categories": WR_CATEGORIES,
        "stat_columns": [
            "targets", "receptions", "catch_rate", "rec_yards",
            "yards_per_reception", "yards_per_target", "rec_tds",
            "first_downs", "longest_rec", "yards_after_catch", "fumbles"
        ],
    },
    "TE": {
        "id": "TE",
        "name": "Tight Ends",
        "data_source": "receiving",
        "positions": ["TE"],
        "categories": TE_CATEGORIES,
        "stat_columns": [
            "targets", "receptions", "catch_rate", "rec_yards",
            "yards_per_reception", "yards_per_target", "rec_tds",
            "first_downs", "longest_rec", "yards_after_catch", "fumbles"
        ],
    },
    "K": {
        "id": "K",
        "name": "Kickers",
        "data_source": "kicking",
        "positions": ["K"],
        "categories": K_CATEGORIES,
        "stat_columns": [
            "fg_made", "fg_attempts", "fg_pct", "fg_made_40_49",
            "fg_made_50_plus", "long_fg", "xp_made", "xp_attempts",
            "xp_pct", "total_points"
        ],
    },
}


def get_position_group(group_id: str) -> PositionGroupConfig:
    """Get configuration for a position group by ID."""
    if group_id not in POSITION_GROUPS:
        raise ValueError(f"Unknown position group: {group_id}")
    return POSITION_GROUPS[group_id]


def get_categories_for_group(group_id: str) -> List[CategoryConfig]:
    """Get categories for a position group."""
    return get_position_group(group_id)["categories"]


def get_category_weights(group_id: str) -> Dict[str, float]:
    """Get category weights for a position group as a dict."""
    categories = get_categories_for_group(group_id)
    return {cat["id"]: cat["weight"] for cat in categories}


def get_log_scale_stats(group_id: str) -> Set[str]:
    """Get all stats that should use log scaling for a position group."""
    categories = get_categories_for_group(group_id)
    log_stats: Set[str] = set()
    for cat in categories:
        log_stats.update(cat["log_scale_stats"])
    return log_stats


def get_position_group_list() -> List[Dict]:
    """Get a list of all position groups for the API."""
    result = []
    for group in POSITION_GROUPS.values():
        group_info = {
            "id": group["id"],
            "name": group["name"],
            "categories": [
                {"id": cat["id"], "name": cat["name"]}
                for cat in group["categories"]
            ],
        }
        # Include sub_positions if present
        if "sub_positions" in group:
            group_info["sub_positions"] = group["sub_positions"]
        result.append(group_info)
    return result


# For backward compatibility
CATEGORY_STATS = {cat["id"]: cat["stats"] for cat in DEF_CATEGORIES}
PLAYMAKING_STATS = {"forced_fumbles", "fumble_recoveries", "interceptions", "defensive_tds"}

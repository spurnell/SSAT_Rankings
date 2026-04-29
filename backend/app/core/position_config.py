"""
Position Configuration - Single source of truth for all NFL position groups.

This module defines all position groups, their categories, stats, and weights.
The ranking engine and frontend read from this config rather than hardcoding values.
"""

from typing import Dict, List, TypedDict, Set


# Stats where lower values indicate better performance.
# The ranking engine negates z-scores for these stats so that high values
# correctly penalize a player. The frontend mirrors this set in
# lib/statLabels.ts to reverse per-stat rank ordering in the profile table.
LOWER_IS_BETTER_STATS: Set[str] = {
    # Universal
    "fumbles",
    "fumbles_lost",
    # QB raw stats (renamed in nfl_data_db.py to disambiguate from DEF)
    "interceptions_thrown",
    "sacks_taken",
    "sack_yards",
    # PFF raw stats whose lower-is-better forms are normally surfaced
    # as _inv variants — included here so that if the raw form is ever
    # displayed or scored directly, it is treated correctly.
    "drop_rate",
    "twp_rate",
    "pressure_to_sack_rate",
    "sack_percent",
    "missed_tackle_rate",
    "qb_rating_against",
    "catch_rate_allowed",
    "yards_per_coverage_snap",
    "average_yards_per_return",
}


def is_lower_is_better(stat_name: str) -> bool:
    """Return True if higher values of this stat indicate worse performance."""
    return stat_name in LOWER_IS_BETTER_STATS


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
        "weight": 0.25,
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
        "weight": 0.25,
        "log_scale_stats": [],
    },
    {
        "id": "ball_security",
        "name": "Ball Security",
        "stats": ["int_rate_inv", "sack_rate_inv", "fumbles_inv"],  # _inv = inverted (lower is better)
        "weight": 0.15,
        "log_scale_stats": [],
    },
    {
        "id": "rushing",
        "name": "Rushing",
        "stats": [
            "rush_yards", "rush_tds", "yards_per_carry", "rushing_first_downs",
            # Mobility / pressure-evasion: lower is better, engine inverts via
            # LOWER_IS_BETTER_STATS so a high sack count counts against the QB.
            "sacks_taken", "sack_yards",
        ],
        "weight": 0.15,
        "log_scale_stats": ["rush_tds"],
    },
]

# PFF-based QB categories (alternative view using PFF advanced stats)
PFF_QB_CATEGORIES: List[CategoryConfig] = [
    {
        "id": "pff_accuracy",
        "name": "Accuracy",
        "stats": ["accuracy_percent", "big_time_throws", "drop_rate_inv"],
        "weight": 0.25,
        "log_scale_stats": [],
    },
    {
        "id": "pff_decision_making",
        "name": "Decision Making",
        "stats": ["twp_rate_inv", "thrown_aways", "interceptions_inv"],
        "weight": 0.25,
        "log_scale_stats": [],
    },
    {
        "id": "pff_pocket_presence",
        "name": "Pocket Presence",
        "stats": ["pressure_to_sack_rate_inv", "sack_percent_inv", "scrambles", "hit_as_threw", "fumbles_inv"],
        "weight": 0.20,
        "log_scale_stats": [],
    },
    {
        "id": "pff_playmaking",
        "name": "Playmaking",
        "stats": ["ypa", "touchdowns", "first_downs"],
        "weight": 0.15,
        "log_scale_stats": [],
    },
    {
        "id": "pff_rushing",
        "name": "Rushing",
        # Stats sourced from pff_rushing_2025.csv via _prepare_pff_qb_stats —
        # renamed with rush_ prefix to avoid colliding with passing-CSV columns.
        "stats": [
            "rush_yards", "rush_tds", "rush_ypa",
            "rush_yco_attempt", "rush_elusive_rating", "rush_first_downs",
        ],
        "weight": 0.15,
        "log_scale_stats": ["rush_tds"],
    },
]

PFF_QB_STAT_COLUMNS = [
    "accuracy_percent", "big_time_throws", "drop_rate_inv",
    "twp_rate_inv", "thrown_aways", "interceptions_inv",
    "pressure_to_sack_rate_inv", "sack_percent_inv", "scrambles", "hit_as_threw", "fumbles_inv",
    "ypa", "touchdowns", "first_downs",
    # PFF QB rushing (merged in from pff_rushing_2025.csv)
    "rush_yards", "rush_tds", "rush_ypa", "rush_yco_attempt",
    "rush_elusive_rating", "rush_first_downs", "rush_attempts",
    "rush_breakaway_percent",
]


def get_pff_qb_config():
    """Return PFF QB categories, stat columns, and weights."""
    return {
        "categories": PFF_QB_CATEGORIES,
        "stat_columns": PFF_QB_STAT_COLUMNS,
        "weights": {cat["id"]: cat["weight"] for cat in PFF_QB_CATEGORIES},
    }


# PFF-based RB categories
PFF_RB_CATEGORIES: List[CategoryConfig] = [
    {
        "id": "pff_rushing_efficiency",
        "name": "Rushing Efficiency",
        "stats": ["ypa", "yco_attempt", "elusive_rating"],
        "weight": 0.30,
        "log_scale_stats": [],
    },
    {
        "id": "pff_explosiveness",
        "name": "Explosiveness",
        "stats": ["breakaway_percent", "explosive", "longest"],
        "weight": 0.20,
        "log_scale_stats": [],
    },
    {
        "id": "pff_volume_production",
        "name": "Volume & Production",
        "stats": ["yards", "touchdowns", "first_downs"],
        "weight": 0.25,
        "log_scale_stats": [],
    },
    {
        "id": "pff_ball_security",
        "name": "Ball Security",
        "stats": ["fumbles_inv", "avoided_tackles"],
        "weight": 0.10,
        "log_scale_stats": [],
    },
    {
        "id": "pff_rb_receiving",
        "name": "Receiving",
        "stats": ["receptions", "rec_yards", "yprr"],
        "weight": 0.15,
        "log_scale_stats": [],
    },
]

PFF_RB_STAT_COLUMNS = [
    "ypa", "yco_attempt", "elusive_rating",
    "breakaway_percent", "explosive", "longest",
    "yards", "touchdowns", "first_downs",
    "fumbles_inv", "avoided_tackles",
    "receptions", "rec_yards", "yprr",
]


def get_pff_rb_config():
    """Return PFF RB categories, stat columns, and weights."""
    return {
        "categories": PFF_RB_CATEGORIES,
        "stat_columns": PFF_RB_STAT_COLUMNS,
        "weights": {cat["id"]: cat["weight"] for cat in PFF_RB_CATEGORIES},
    }


# PFF-based WR categories
PFF_WR_CATEGORIES: List[CategoryConfig] = [
    {
        "id": "pff_route_running",
        "name": "Route Running",
        "stats": ["grades_pass_route", "yprr", "route_rate"],
        "weight": 0.30,
        "log_scale_stats": [],
    },
    {
        "id": "pff_hands_catching",
        "name": "Hands & Catching",
        "stats": ["caught_percent", "contested_catch_rate", "drop_rate_inv"],
        "weight": 0.25,
        "log_scale_stats": [],
    },
    {
        "id": "pff_wr_playmaking",
        "name": "Playmaking",
        "stats": ["yards_after_catch_per_reception", "touchdowns", "first_downs", "avoided_tackles"],
        "weight": 0.25,
        "log_scale_stats": [],
    },
    {
        "id": "pff_wr_production",
        "name": "Production",
        "stats": ["yards", "receptions", "targeted_qb_rating"],
        "weight": 0.20,
        "log_scale_stats": [],
    },
]

PFF_WR_STAT_COLUMNS = [
    "grades_pass_route", "yprr", "route_rate",
    "caught_percent", "contested_catch_rate", "drop_rate_inv",
    "yards_after_catch_per_reception", "touchdowns", "first_downs", "avoided_tackles",
    "yards", "receptions", "targeted_qb_rating",
]


def get_pff_wr_config():
    """Return PFF WR categories, stat columns, and weights."""
    return {
        "categories": PFF_WR_CATEGORIES,
        "stat_columns": PFF_WR_STAT_COLUMNS,
        "weights": {cat["id"]: cat["weight"] for cat in PFF_WR_CATEGORIES},
    }


# PFF-based TE categories
PFF_TE_CATEGORIES: List[CategoryConfig] = [
    {
        "id": "pff_te_receiving",
        "name": "Receiving",
        "stats": ["yards", "receptions", "yprr", "caught_percent"],
        "weight": 0.30,
        "log_scale_stats": [],
    },
    {
        "id": "pff_te_route_running",
        "name": "Route Running",
        "stats": ["grades_pass_route", "avg_depth_of_target", "yards_per_reception"],
        "weight": 0.20,
        "log_scale_stats": [],
    },
    {
        "id": "pff_contested_catching",
        "name": "Contested Catching",
        "stats": ["contested_catch_rate", "drop_rate_inv", "touchdowns"],
        "weight": 0.15,
        "log_scale_stats": [],
    },
    {
        "id": "pff_blocking",
        "name": "Blocking",
        "stats": ["grades_pass_block", "pass_block_percent", "pressures_allowed_inv"],
        "weight": 0.20,
        "log_scale_stats": [],
    },
    {
        "id": "pff_te_playmaking",
        "name": "Playmaking",
        "stats": ["yards_after_catch_per_reception", "first_downs", "avoided_tackles"],
        "weight": 0.15,
        "log_scale_stats": [],
    },
]

PFF_TE_STAT_COLUMNS = [
    "yards", "receptions", "yprr", "caught_percent",
    "grades_pass_route", "avg_depth_of_target", "yards_per_reception",
    "contested_catch_rate", "drop_rate_inv", "touchdowns",
    "grades_pass_block", "pass_block_percent", "pressures_allowed_inv",
    "yards_after_catch_per_reception", "first_downs", "avoided_tackles",
]


def get_pff_te_config():
    """Return PFF TE categories, stat columns, and weights."""
    return {
        "categories": PFF_TE_CATEGORIES,
        "stat_columns": PFF_TE_STAT_COLUMNS,
        "weights": {cat["id"]: cat["weight"] for cat in PFF_TE_CATEGORIES},
    }


# PFF-based DEF Front 7 categories (DL, EDGE, LB)
PFF_DEF_FRONT7_CATEGORIES: List[CategoryConfig] = [
    {
        "id": "pff_pass_rush",
        "name": "Pass Rush",
        "stats": ["grades_pass_rush_defense", "pass_rush_win_rate", "total_pressures", "prp"],
        "weight": 0.30,
        "log_scale_stats": [],
    },
    {
        "id": "pff_run_defense",
        "name": "Run Defense",
        "stats": ["grades_run_defense", "stop_percent", "tackles", "missed_tackle_rate_inv"],
        "weight": 0.30,
        "log_scale_stats": [],
    },
    {
        "id": "pff_tackling",
        "name": "Tackling",
        "stats": ["grades_tackle", "missed_tackle_rate_inv", "stops"],
        "weight": 0.20,
        "log_scale_stats": [],
    },
    {
        "id": "pff_f7_playmaking",
        "name": "Playmaking",
        "stats": ["sacks", "interceptions", "forced_fumbles", "pass_break_ups"],
        "weight": 0.20,
        "log_scale_stats": [],
    },
]

PFF_DEF_FRONT7_STAT_COLUMNS = [
    "grades_pass_rush_defense", "pass_rush_win_rate", "total_pressures", "prp",
    "grades_run_defense", "stop_percent", "tackles", "missed_tackle_rate_inv",
    "grades_tackle", "stops",
    "sacks", "interceptions", "forced_fumbles", "pass_break_ups",
]


def get_pff_def_front7_config():
    """Return PFF DEF Front 7 categories, stat columns, and weights."""
    return {
        "categories": PFF_DEF_FRONT7_CATEGORIES,
        "stat_columns": PFF_DEF_FRONT7_STAT_COLUMNS,
        "weights": {cat["id"]: cat["weight"] for cat in PFF_DEF_FRONT7_CATEGORIES},
    }


# PFF-based DEF Secondary categories (CB, S)
PFF_DEF_SECONDARY_CATEGORIES: List[CategoryConfig] = [
    {
        "id": "pff_sec_coverage",
        "name": "Coverage",
        "stats": ["grades_coverage_defense", "qb_rating_against_inv", "catch_rate_inv", "forced_incompletion_rate", "coverage_snaps_per_target"],
        "weight": 0.35,
        "log_scale_stats": [],
    },
    {
        "id": "pff_sec_tackling",
        "name": "Tackling",
        "stats": ["grades_tackle", "missed_tackle_rate_inv", "tackles", "stops"],
        "weight": 0.25,
        "log_scale_stats": [],
    },
    {
        "id": "pff_sec_playmaking",
        "name": "Playmaking",
        "stats": ["interceptions", "pass_break_ups", "forced_fumbles"],
        "weight": 0.20,
        "log_scale_stats": [],
    },
    {
        "id": "pff_ball_hawking",
        "name": "Ball Hawking",
        "stats": ["interceptions", "coverage_snaps_per_reception", "yards_per_coverage_snap_inv"],
        "weight": 0.20,
        "log_scale_stats": [],
    },
]

PFF_DEF_SECONDARY_STAT_COLUMNS = [
    "grades_coverage_defense", "qb_rating_against_inv", "catch_rate_inv", "forced_incompletion_rate", "coverage_snaps_per_target",
    "grades_tackle", "missed_tackle_rate_inv", "tackles", "stops",
    "interceptions", "pass_break_ups", "forced_fumbles",
    "coverage_snaps_per_reception", "yards_per_coverage_snap_inv",
]


def get_pff_def_secondary_config():
    """Return PFF DEF Secondary categories, stat columns, and weights."""
    return {
        "categories": PFF_DEF_SECONDARY_CATEGORIES,
        "stat_columns": PFF_DEF_SECONDARY_STAT_COLUMNS,
        "weights": {cat["id"]: cat["weight"] for cat in PFF_DEF_SECONDARY_CATEGORIES},
    }


# Coverage-only PFF source — surfaced to the custom-builder bubble grid for
# LB/CB/S so off-ball linebackers get coverage stats alongside defensive
# backs. Stats come straight from pff_coverage_2025.csv (no merge with
# pff_defense_2025.csv), keeping the column set focused on coverage.
PFF_COVERAGE_CATEGORIES: List[CategoryConfig] = [
    {
        "id": "pff_cov_quality",
        "name": "Coverage Quality",
        "stats": [
            "grades_coverage_defense",
            "qb_rating_against_inv",
            "catch_rate_inv",
            "forced_incompletion_rate",
        ],
        "weight": 0.45,
        "log_scale_stats": [],
    },
    {
        "id": "pff_cov_density",
        "name": "Coverage Density",
        "stats": [
            "coverage_snaps_per_target",
            "coverage_snaps_per_reception",
            "yards_per_coverage_snap_inv",
        ],
        "weight": 0.25,
        "log_scale_stats": [],
    },
    {
        "id": "pff_cov_playmaking",
        "name": "Ball Hawking",
        "stats": ["interceptions", "pass_break_ups", "forced_incompletes"],
        "weight": 0.30,
        "log_scale_stats": [],
    },
]

PFF_COVERAGE_STAT_COLUMNS = [
    "grades_coverage_defense",
    "qb_rating_against_inv",
    "catch_rate_inv",
    "forced_incompletion_rate",
    "coverage_snaps_per_target",
    "coverage_snaps_per_reception",
    "yards_per_coverage_snap_inv",
    "interceptions",
    "pass_break_ups",
    "forced_incompletes",
]


def get_pff_coverage_config():
    """Return PFF Coverage (LB/CB/S) categories, stat columns, and weights."""
    return {
        "categories": PFF_COVERAGE_CATEGORIES,
        "stat_columns": PFF_COVERAGE_STAT_COLUMNS,
        "weights": {cat["id"]: cat["weight"] for cat in PFF_COVERAGE_CATEGORIES},
    }


# PFF-based K categories
PFF_K_CATEGORIES: List[CategoryConfig] = [
    {
        "id": "pff_k_accuracy",
        "name": "Accuracy",
        "stats": ["total_percent", "pat_percent", "grades_fgep_kicker"],
        "weight": 0.35,
        "log_scale_stats": [],
    },
    {
        "id": "pff_range_power",
        "name": "Range & Power",
        "stats": ["fifty_percent", "forty_percent", "fifty_made"],
        "weight": 0.25,
        "log_scale_stats": [],
    },
    {
        "id": "pff_k_volume",
        "name": "Volume",
        "stats": ["total_made", "pat_made"],
        "weight": 0.15,
        "log_scale_stats": [],
    },
    {
        "id": "pff_kickoffs",
        "name": "Kickoffs",
        "stats": ["grades_kickoff_kicker", "touchbacks", "average_yards_per_return_inv"],
        "weight": 0.25,
        "log_scale_stats": [],
    },
]

PFF_K_STAT_COLUMNS = [
    "total_percent", "pat_percent", "grades_fgep_kicker",
    "fifty_percent", "forty_percent", "fifty_made",
    "total_made", "pat_made",
    "grades_kickoff_kicker", "touchbacks", "average_yards_per_return_inv",
]


def get_pff_k_config():
    """Return PFF K categories, stat columns, and weights."""
    return {
        "categories": PFF_K_CATEGORIES,
        "stat_columns": PFF_K_STAT_COLUMNS,
        "weights": {cat["id"]: cat["weight"] for cat in PFF_K_CATEGORIES},
    }


# Unified PFF config accessor
def get_pff_config(position_group: str, source: str = "pff"):
    """Return PFF config for any position group, or None if not available.

    For DEF, use source='pff_front7' or 'pff_secondary' to get the specific config.
    """
    # Handle DEF split sources
    if position_group == "DEF":
        if source == "pff_front7":
            return get_pff_def_front7_config()
        elif source == "pff_secondary":
            return get_pff_def_secondary_config()
        elif source == "pff_coverage":
            return get_pff_coverage_config()
        return None  # DEF has no generic "pff" source

    configs = {
        "QB": get_pff_qb_config,
        "RB": get_pff_rb_config,
        "WR": get_pff_wr_config,
        "TE": get_pff_te_config,
        "K": get_pff_k_config,
    }
    getter = configs.get(position_group)
    return getter() if getter else None


def has_pff_source(position_group: str) -> bool:
    """Check if a position group has any PFF source available."""
    if position_group == "DEF":
        return True  # DEF has front7 + secondary
    return get_pff_config(position_group) is not None


# Running back config
RB_CATEGORIES: List[CategoryConfig] = [
    {
        "id": "efficiency",
        "name": "Efficiency",
        "stats": ["yards_per_carry", "yards_per_touch", "success_rate", "fumbles"],
        "weight": 0.30,
        "log_scale_stats": ["fumbles"],
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
        "stats": ["yards_per_reception", "yards_per_target", "catch_rate", "fumbles"],
        "weight": 0.25,
        "log_scale_stats": ["fumbles"],
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
        "stats": ["yards_per_reception", "catch_rate", "yards_per_target", "fumbles"],
        "weight": 0.30,
        "log_scale_stats": ["fumbles"],
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
            "pass_tds", "interceptions_thrown", "passer_rating", "yards_per_attempt",
            "sacks_taken", "sack_yards", "first_downs", "fumbles",
            "int_rate_inv", "sack_rate_inv", "fumbles_inv",
            # Rushing (mobile QBs)
            "rush_attempts", "rush_yards", "rush_tds", "yards_per_carry",
            "rushing_first_downs",
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
                {"id": cat["id"], "name": cat["name"], "stats": cat.get("stats", [])}
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

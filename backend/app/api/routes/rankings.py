from typing import List, Optional, Dict

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.models.schemas import (
    PlayerRanking,
    PlayerDetail,
    PositionGroupInfo,
    CategoryInfo,
    LegacyPlayerDetail,
    PlayerStats,
)
from app.services.nfl_data_db import process_player_rankings, get_available_seasons
from app.services.pff_data import process_pff_rankings
from app.services.custom_categories import process_custom_category_rankings
from app.core.position_config import (
    get_position_group_list,
    POSITION_GROUPS,
    get_pff_config,
    has_pff_source,
    LOWER_IS_BETTER_STATS,
)

router = APIRouter()

# Cache for player data by position group
_player_cache: Dict[str, List[Dict]] = {}


def get_cached_rankings(position_group: str = "DEF") -> List[Dict]:
    """Get cached rankings for a position group."""
    global _player_cache
    if position_group not in _player_cache:
        _player_cache[position_group] = process_player_rankings(position_group=position_group)
    return _player_cache[position_group]


def clear_cache():
    """Clear the rankings cache."""
    global _player_cache
    _player_cache = {}


@router.get("/position-groups", response_model=List[PositionGroupInfo])
async def get_position_groups():
    """
    Get list of all available position groups with their categories.
    """
    results = []
    for group in get_position_group_list():
        info = PositionGroupInfo(
            id=group["id"],
            name=group["name"],
            categories=[
                CategoryInfo(id=cat["id"], name=cat["name"], stats=cat.get("stats", []))
                for cat in group["categories"]
            ],
            sub_positions=group.get("sub_positions"),
        )
        # Add PFF source info for groups that have PFF configs
        if group["id"] == "DEF":
            # DEF has two PFF sub-sources: front7 and secondary
            info.available_sources = ["standard", "pff_front7", "pff_secondary"]
            front7_config = get_pff_config("DEF", source="pff_front7")
            secondary_config = get_pff_config("DEF", source="pff_secondary")
            if front7_config:
                info.pff_front7_categories = [
                    CategoryInfo(id=cat["id"], name=cat["name"], stats=cat.get("stats", []))
                    for cat in front7_config["categories"]
                ]
            if secondary_config:
                info.pff_secondary_categories = [
                    CategoryInfo(id=cat["id"], name=cat["name"], stats=cat.get("stats", []))
                    for cat in secondary_config["categories"]
                ]
        else:
            pff_config = get_pff_config(group["id"])
            if pff_config:
                info.available_sources = ["standard", "pff"]
                info.pff_categories = [
                    CategoryInfo(id=cat["id"], name=cat["name"], stats=cat.get("stats", []))
                    for cat in pff_config["categories"]
                ]
        results.append(info)
    return results


@router.get("/position-config/{position_group}")
async def get_position_config(
    position_group: str,
    source: Optional[str] = Query(None, description="Data source: 'pff' for PFF stats"),
):
    """
    Get detailed position config including category weights and sub-positions.
    """
    if position_group not in POSITION_GROUPS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid position group. Valid groups: {list(POSITION_GROUPS.keys())}"
        )

    if source and source.startswith("pff"):
        pff_config = get_pff_config(position_group, source=source)
        if pff_config:
            group = POSITION_GROUPS[position_group]
            suffix = {"pff_front7": " (PFF Front 7)", "pff_secondary": " (PFF Secondary)"}.get(source, " (PFF)")
            return {
                "id": position_group,
                "name": f"{group['name']}{suffix}",
                "categories": [
                    {
                        "id": cat["id"],
                        "name": cat["name"],
                        "weight": cat["weight"],
                        "stats": cat.get("stats", []),
                    }
                    for cat in pff_config["categories"]
                ],
                "sub_positions": group.get("sub_positions", []),
            }

    group = POSITION_GROUPS[position_group]
    return {
        "id": group["id"],
        "name": group["name"],
        "categories": [
            {
                "id": cat["id"],
                "name": cat["name"],
                "weight": cat["weight"],
                "stats": cat.get("stats", []),
            }
            for cat in group["categories"]
        ],
        "sub_positions": group.get("sub_positions", []),
    }


@router.get("/available-seasons")
async def available_seasons():
    """Get list of seasons that have data in the database."""
    return get_available_seasons()


# Display-name overrides for stats whose snake_case form doesn't title-case nicely.
# Anything not listed falls back to ``stat_name.replace("_", " ").title()``.
_STAT_DISPLAY_OVERRIDES: Dict[str, str] = {
    "qb_hits": "QB Hits",
    "tackles_for_loss": "Tackles for Loss",
    "passes_defended": "Passes Defended",
    "fumble_recoveries": "Fumble Recoveries",
    "defensive_tds": "Defensive TDs",
    "rush_tds": "Rush TDs",
    "rec_tds": "Receiving TDs",
    "pass_tds": "Pass TDs",
    "total_tds": "Total TDs",
    "rec_yards": "Receiving Yards",
    "rush_yards": "Rush Yards",
    "pass_yards": "Pass Yards",
    "yards_per_carry": "Yards / Carry",
    "yards_per_touch": "Yards / Touch",
    "yards_per_reception": "Yards / Reception",
    "yards_per_target": "Yards / Target",
    "yards_per_attempt": "Yards / Attempt",
    "completion_pct": "Completion %",
    "catch_rate": "Catch Rate",
    "passer_rating": "Passer Rating",
    "first_downs": "First Downs",
    "rushing_first_downs": "Rushing First Downs",
    "rush_yards": "Rush Yards",
    "rush_tds": "Rush TDs",
    "rush_ypa": "Rush Yds / Attempt",
    "rush_yco_attempt": "Rush YCO / Attempt",
    "rush_elusive_rating": "Rush Elusive Rating",
    "rush_first_downs": "Rush First Downs",
    "rush_attempts": "Rush Attempts",
    "rush_breakaway_percent": "Rush Breakaway %",
    "longest_rec": "Longest Reception",
    "longest_rush": "Longest Rush",
    "yards_after_catch": "Yards After Catch",
    "yards_after_catch_per_reception": "YAC / Reception",
    "fg_made": "FG Made",
    "fg_attempts": "FG Attempts",
    "fg_pct": "FG %",
    "fg_made_40_49": "FG Made 40–49",
    "fg_made_50_plus": "FG Made 50+",
    "long_fg": "Longest FG",
    "xp_made": "XP Made",
    "xp_attempts": "XP Attempts",
    "xp_pct": "XP %",
    "total_points": "Total Points",
    "int_rate_inv": "INT Rate (inverted)",
    "sack_rate_inv": "Sack Rate (inverted)",
    "fumbles_inv": "Fumbles (inverted)",
    "interceptions_inv": "Interceptions (inverted)",
    "interceptions_thrown": "Interceptions Thrown",
    "sacks_taken": "Sacks Taken",
    "sack_yards": "Sack Yards",
    "drop_rate_inv": "Drop Rate (inverted)",
    "twp_rate_inv": "TWP Rate (inverted)",
    "pressure_to_sack_rate_inv": "Pressure→Sack Rate (inv)",
    "sack_percent_inv": "Sack % (inverted)",
    "missed_tackle_rate_inv": "Missed Tackle Rate (inv)",
    "qb_rating_against_inv": "QB Rating Against (inv)",
    "catch_rate_inv": "Catch Rate Allowed (inv)",
    "yards_per_coverage_snap_inv": "Yds / Cov Snap (inv)",
    "average_yards_per_return_inv": "Avg Return Yds (inv)",
    "pressures_allowed_inv": "Pressures Allowed (inv)",
    "ypa": "Yards per Attempt",
    "yco_attempt": "YCO / Attempt",
    "yprr": "Yards / Route Run",
    "elusive_rating": "Elusive Rating",
    "breakaway_percent": "Breakaway %",
    "explosive": "Explosive Plays",
    "avoided_tackles": "Avoided Tackles",
    "grades_pass_route": "Pass Route Grade",
    "grades_pass_block": "Pass Block Grade",
    "grades_pass_rush_defense": "Pass Rush Grade",
    "grades_run_defense": "Run Defense Grade",
    "grades_coverage_defense": "Coverage Grade",
    "grades_tackle": "Tackle Grade",
    "grades_fgep_kicker": "FG Kicker Grade",
    "grades_kickoff_kicker": "Kickoff Grade",
    "pass_rush_win_rate": "Pass Rush Win %",
    "total_pressures": "Total Pressures",
    "stop_percent": "Stop %",
    "pass_break_ups": "Pass Break-ups",
    "forced_incompletion_rate": "Forced Incompletion %",
    "coverage_snaps_per_target": "Cov Snaps / Target",
    "coverage_snaps_per_reception": "Cov Snaps / Reception",
    "contested_catch_rate": "Contested Catch Rate",
    "caught_percent": "Caught %",
    "route_rate": "Route Rate",
    "targeted_qb_rating": "Targeted QB Rating",
    "avg_depth_of_target": "ADoT",
    "big_time_throws": "Big-Time Throws",
    "thrown_aways": "Thrown Aways",
    "hit_as_threw": "Hit as Threw",
    "scrambles": "Scrambles",
    "accuracy_percent": "Accuracy %",
    "pat_made": "PAT Made",
    "pat_percent": "PAT %",
    "fifty_made": "50+ FG Made",
    "fifty_percent": "50+ FG %",
    "forty_percent": "40–49 FG %",
    "total_made": "Total FG Made",
    "total_percent": "Total FG %",
    "touchbacks": "Touchbacks",
    "prp": "Pass Rush Productivity",
}


def _display_name(stat_name: str) -> str:
    """Convert a snake_case stat name to a friendly display string."""
    if stat_name in _STAT_DISPLAY_OVERRIDES:
        return _STAT_DISPLAY_OVERRIDES[stat_name]
    return stat_name.replace("_", " ").title()


def _is_inverted(stat_name: str) -> bool:
    """Whether the stat is an _inv-style derived metric (already framed as higher-is-better)."""
    return stat_name.endswith("_inv")


def _build_source_stat_entries(
    position_group: str,
    source: str,
    categories: List[Dict],
) -> List[Dict]:
    """Flatten every stat in a source's category list into available-stats entries."""
    log_set: set = set()
    for cat in categories:
        log_set.update(cat.get("log_scale_stats", []))

    seen: set = set()
    entries: List[Dict] = []
    for cat in categories:
        for stat in cat.get("stats", []):
            if stat in seen:
                continue
            seen.add(stat)
            higher_is_better = (
                _is_inverted(stat) or stat not in LOWER_IS_BETTER_STATS
            )
            entries.append({
                "key": f"{source}::{stat}",
                "source": source,
                "name": stat,
                "display_name": _display_name(stat),
                "higher_is_better": higher_is_better,
                "log_scale": stat in log_set,
                "default_category": cat["id"],
            })
    return entries


# DEF sub-position → which PFF sources the bubble grid surfaces for that
# position. Pure pass-rush / run-defense stats live in pff_front7 and only
# apply to the front seven (DL/EDGE/LB). Coverage stats live in pff_coverage
# and apply to anyone who drops into coverage (LB/CB/S). DL/EDGE never get
# coverage stats; CB/S never get front-7 stats. LBs get both because they
# show up in both the run-game and coverage pictures.
#
# "All" surfaces only the standard source — no PFF — because no single
# combination of PFF sources is valid for the entire defensive roster
# (mixing would empty the inner join in process_custom_category_rankings).
_DEF_FRONT7_ONLY_POSITIONS = {"DL", "EDGE"}
_DEF_LB_POSITIONS = {"LB"}
_DEF_COVERAGE_ONLY_POSITIONS = {"CB", "S"}


@router.get("/available-stats/{position_group}")
async def get_available_stats(
    position_group: str,
    position: Optional[str] = Query(
        None,
        description=(
            "Sub-position filter (DEF only). Restricts which PFF sources are "
            "exposed so the bubble grid only shows stats every player in the "
            "selected pool actually has. Pass 'All' or omit for the broadest "
            "set."
        ),
    ),
):
    """List every stat available for a position group across all sources.

    Drives the bubble grid in the custom-category builder. The ``key`` field
    is what the frontend should send back in ``CalculateRequest.categories``
    via ``{"source": ..., "name": ...}``.

    For DEF, the response is filtered by ``position`` so users can't pick
    incompatible cross-source combinations (which would empty the join).
    """
    if position_group not in POSITION_GROUPS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid position group. Valid groups: {list(POSITION_GROUPS.keys())}",
        )

    sources_payload: List[Dict] = []

    # Standard source — always available, every player has these stats.
    standard_categories = POSITION_GROUPS[position_group]["categories"]
    sources_payload.append({
        "source": "standard",
        "label": "Standard (nflverse)",
        "stats": _build_source_stat_entries(position_group, "standard", standard_categories),
    })

    # PFF sources — gated by sub-position for DEF.
    if position_group == "DEF":
        normalized = (position or "All").strip()
        if normalized in _DEF_FRONT7_ONLY_POSITIONS:
            allowed_pff_sources = [("pff_front7", "PFF — Front 7")]
        elif normalized in _DEF_LB_POSITIONS:
            # LBs play in both the box and in coverage — surface both sources.
            # The compute path's inner join naturally narrows to LBs since
            # they're the only shared position.
            allowed_pff_sources = [
                ("pff_front7", "PFF — Front 7"),
                ("pff_coverage", "PFF — Coverage"),
            ]
        elif normalized in _DEF_COVERAGE_ONLY_POSITIONS:
            allowed_pff_sources = [("pff_coverage", "PFF — Coverage")]
        else:
            # "All" — no defensive sub-position pool covers every PFF source,
            # so we surface only the standard stats.
            allowed_pff_sources = []
        for src, label in allowed_pff_sources:
            cfg = get_pff_config("DEF", source=src)
            if cfg:
                sources_payload.append({
                    "source": src,
                    "label": label,
                    "stats": _build_source_stat_entries(position_group, src, cfg["categories"]),
                })
    else:
        cfg = get_pff_config(position_group)
        if cfg:
            sources_payload.append({
                "source": "pff",
                "label": "PFF",
                "stats": _build_source_stat_entries(position_group, "pff", cfg["categories"]),
            })

    return {
        "position_group": position_group,
        "sources": sources_payload,
    }


@router.get("/rankings/{position_group}", response_model=List[PlayerDetail])
async def get_rankings_by_group(
    position_group: str,
    position: Optional[str] = Query(None, description="Filter by sub-position (for DEF group)"),
    min_games: int = Query(1, ge=1, le=17, description="Minimum games played"),
    season: Optional[int] = Query(None, description="Season year (default: current season)"),
    source: Optional[str] = Query(None, description="Data source: 'pff' for PFF stats"),
):
    """
    Get ranked list of players for a specific position group.

    Position groups: DEF, QB, RB, WR, TE, K
    """
    if position_group not in POSITION_GROUPS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid position group. Valid groups: {list(POSITION_GROUPS.keys())}"
        )

    # PFF source
    if source and source.startswith("pff") and get_pff_config(position_group, source=source):
        rankings = process_pff_rankings(
            position_group=position_group,
            min_games=min_games,
            position_filter=position,
            source=source,
            season=season,
        )
    else:
        rankings = process_player_rankings(
            min_games=min_games,
            position_filter=position,
            position_group=position_group,
            season=season,
        )

    return [
        PlayerDetail(
            id=p["id"],
            name=p["name"],
            team=p["team"],
            position=p["position"],
            games_played=p["games_played"],
            overall_score=p["overall_score"],
            position_group=p["position_group"],
            category_scores=p["category_scores"],
            stats=p["stats"],
        )
        for p in rankings
    ]


@router.get("/rankings", response_model=List[LegacyPlayerDetail])
async def get_rankings(
    position: Optional[str] = Query(None, description="Filter by position (DL, EDGE, LB, CB, S)"),
    min_games: int = Query(1, ge=1, le=17, description="Minimum games played"),
):
    """
    Get ranked list of defensive players (legacy endpoint for backward compatibility).
    Optionally filter by position and minimum games played.
    """
    rankings = process_player_rankings(
        min_games=min_games,
        position_filter=position,
        position_group="DEF",
    )

    # Convert to legacy format
    return [
        LegacyPlayerDetail(
            id=p["id"],
            name=p["name"],
            team=p["team"],
            position=p["position"],
            games_played=p["games_played"],
            overall_score=p["overall_score"],
            run_defense_score=p["category_scores"].get("run_defense", 80.0),
            pass_rush_score=p["category_scores"].get("pass_rush", 80.0),
            coverage_score=p["category_scores"].get("coverage", 80.0),
            playmaking_score=p["category_scores"].get("playmaking", 80.0),
            stats=PlayerStats(**{
                k: v for k, v in p["stats"].items()
                if k in PlayerStats.model_fields
            }),
        )
        for p in rankings
    ]


@router.get("/players/{player_id}", response_model=LegacyPlayerDetail)
async def get_player(
    player_id: int,
    position_group: str = Query("DEF", description="Position group to search in"),
):
    """Get detailed information for a specific player."""
    rankings = get_cached_rankings(position_group)

    player = next((p for p in rankings if p["id"] == player_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # For DEF position group, return legacy format
    if position_group == "DEF":
        return LegacyPlayerDetail(
            id=player["id"],
            name=player["name"],
            team=player["team"],
            position=player["position"],
            games_played=player["games_played"],
            overall_score=player["overall_score"],
            run_defense_score=player["category_scores"].get("run_defense", 80.0),
            pass_rush_score=player["category_scores"].get("pass_rush", 80.0),
            coverage_score=player["category_scores"].get("coverage", 80.0),
            playmaking_score=player["category_scores"].get("playmaking", 80.0),
            stats=PlayerStats(**{
                k: v for k, v in player["stats"].items()
                if k in PlayerStats.model_fields
            }),
        )

    # For other position groups, return new format (but using legacy response model for now)
    return LegacyPlayerDetail(
        id=player["id"],
        name=player["name"],
        team=player["team"],
        position=player["position"],
        games_played=player["games_played"],
        overall_score=player["overall_score"],
        run_defense_score=80.0,
        pass_rush_score=80.0,
        coverage_score=80.0,
        playmaking_score=80.0,
        stats=PlayerStats(),
    )


@router.get("/compare", response_model=List[LegacyPlayerDetail])
async def compare_players(
    ids: str = Query(..., description="Comma-separated player IDs to compare"),
    position_group: str = Query("DEF", description="Position group"),
):
    """Compare multiple players side by side."""
    try:
        player_ids = [int(id.strip()) for id in ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid player IDs format")

    if len(player_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 players to compare")
    if len(player_ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 players can be compared")

    rankings = get_cached_rankings(position_group)
    players = []

    for pid in player_ids:
        player = next((p for p in rankings if p["id"] == pid), None)
        if player:
            players.append(
                LegacyPlayerDetail(
                    id=player["id"],
                    name=player["name"],
                    team=player["team"],
                    position=player["position"],
                    games_played=player["games_played"],
                    overall_score=player["overall_score"],
                    run_defense_score=player["category_scores"].get("run_defense", 80.0),
                    pass_rush_score=player["category_scores"].get("pass_rush", 80.0),
                    coverage_score=player["category_scores"].get("coverage", 80.0),
                    playmaking_score=player["category_scores"].get("playmaking", 80.0),
                    stats=PlayerStats(**{
                        k: v for k, v in player["stats"].items()
                        if k in PlayerStats.model_fields
                    }),
                )
            )

    if not players:
        raise HTTPException(status_code=404, detail="No players found with given IDs")

    return players


class CustomCategoryStat(BaseModel):
    """A single stat selected by the user for a custom category."""
    source: str  # "standard" | "pff" | "pff_front7" | "pff_secondary"
    name: str


class CustomCategory(BaseModel):
    """A user-defined sub-category in the custom-category builder."""
    id: str
    name: str
    weight: float = 1.0
    stats: List[CustomCategoryStat]


class CalculateRequest(BaseModel):
    """Request body for custom weight calculations."""
    position_group: str = "DEF"
    weights: Optional[Dict[str, float]] = None
    categories: Optional[List[CustomCategory]] = None  # user-defined categories
    min_games: int = 1
    position: Optional[str] = None
    mode: Optional[str] = None  # "season", "career_cumulative", "career_per_game"
    min_seasons: Optional[int] = None
    source: Optional[str] = None  # "pff" for PFF stats — ignored when categories is set


@router.post("/calculate", response_model=List[PlayerDetail])
async def calculate_rankings(body: CalculateRequest):
    """
    Calculate rankings with custom weights or user-defined categories.

    If ``categories`` is provided, runs the multi-source compute path that
    can mix standard + PFF stats within a single ranking. Otherwise falls
    back to the legacy weights-only path.
    """
    if body.position_group not in POSITION_GROUPS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid position group. Valid groups: {list(POSITION_GROUPS.keys())}"
        )

    if body.categories:
        custom_payload = [c.model_dump() for c in body.categories]
        try:
            rankings = process_custom_category_rankings(
                position_group=body.position_group,
                custom_categories=custom_payload,
                min_games=body.min_games,
                position_filter=body.position,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif body.source and body.source.startswith("pff") and get_pff_config(body.position_group, source=body.source):
        rankings = process_pff_rankings(
            position_group=body.position_group,
            min_games=body.min_games,
            weights=body.weights,
            position_filter=body.position,
            source=body.source,
        )
    else:
        rankings = process_player_rankings(
            min_games=body.min_games,
            position_filter=body.position,
            weights=body.weights,
            position_group=body.position_group,
        )

    return [
        PlayerDetail(
            id=p["id"],
            name=p["name"],
            team=p["team"],
            position=p["position"],
            games_played=p["games_played"],
            overall_score=p["overall_score"],
            position_group=p["position_group"],
            category_scores=p["category_scores"],
            stats=p["stats"],
        )
        for p in rankings
    ]

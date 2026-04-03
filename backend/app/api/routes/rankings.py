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
from app.services.pff_data import process_pff_qb_rankings
from app.core.position_config import get_position_group_list, POSITION_GROUPS, PFF_QB_CATEGORIES

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
                CategoryInfo(id=cat["id"], name=cat["name"])
                for cat in group["categories"]
            ],
            sub_positions=group.get("sub_positions"),
        )
        # Add PFF source info for QB
        if group["id"] == "QB":
            info.available_sources = ["standard", "pff"]
            info.pff_categories = [
                CategoryInfo(id=cat["id"], name=cat["name"])
                for cat in PFF_QB_CATEGORIES
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

    if source == "pff" and position_group == "QB":
        return {
            "id": "QB",
            "name": "Quarterbacks (PFF)",
            "categories": [
                {"id": cat["id"], "name": cat["name"], "weight": cat["weight"]}
                for cat in PFF_QB_CATEGORIES
            ],
            "sub_positions": [],
        }

    group = POSITION_GROUPS[position_group]
    return {
        "id": group["id"],
        "name": group["name"],
        "categories": [
            {"id": cat["id"], "name": cat["name"], "weight": cat["weight"]}
            for cat in group["categories"]
        ],
        "sub_positions": group.get("sub_positions", []),
    }


@router.get("/available-seasons")
async def available_seasons():
    """Get list of seasons that have data in the database."""
    return get_available_seasons()


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

    # PFF source for QBs
    if source == "pff" and position_group == "QB":
        rankings = process_pff_qb_rankings(min_games=min_games)
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


class CalculateRequest(BaseModel):
    """Request body for custom weight calculations."""
    position_group: str = "DEF"
    weights: Optional[Dict[str, float]] = None
    min_games: int = 1
    position: Optional[str] = None
    mode: Optional[str] = None  # "season", "career_cumulative", "career_per_game"
    min_seasons: Optional[int] = None
    source: Optional[str] = None  # "pff" for PFF stats


@router.post("/calculate", response_model=List[PlayerDetail])
async def calculate_rankings(body: CalculateRequest):
    """
    Calculate rankings with custom weights.

    Weights should sum to 1.0 for proper scaling.
    """
    if body.position_group not in POSITION_GROUPS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid position group. Valid groups: {list(POSITION_GROUPS.keys())}"
        )

    if body.source == "pff" and body.position_group == "QB":
        rankings = process_pff_qb_rankings(
            min_games=body.min_games,
            weights=body.weights,
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

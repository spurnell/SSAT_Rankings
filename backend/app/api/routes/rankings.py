from typing import List, Optional, Dict

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import PlayerRanking, PlayerDetail, CategoryWeights, PlayerStats
from app.services.nfl_data import process_player_rankings

router = APIRouter()

# Cache for player data
_player_cache: Optional[List[Dict]] = None


def get_cached_rankings() -> List[Dict]:
    global _player_cache
    if _player_cache is None:
        _player_cache = process_player_rankings()
    return _player_cache


@router.get("/rankings", response_model=List[PlayerRanking])
async def get_rankings(
    position: Optional[str] = Query(None, description="Filter by position (DL, EDGE, LB, CB, S)"),
    min_games: int = Query(1, ge=1, le=17, description="Minimum games played"),
):
    """
    Get ranked list of defensive players.
    Optionally filter by position and minimum games played.
    """
    weights = None  # Use default equal weights

    rankings = process_player_rankings(
        min_games=min_games,
        position_filter=position,
        weights=weights,
    )

    return [
        PlayerRanking(
            id=p["id"],
            name=p["name"],
            team=p["team"],
            position=p["position"],
            games_played=p["games_played"],
            overall_score=p["overall_score"],
            run_defense_score=p["run_defense_score"],
            pass_rush_score=p["pass_rush_score"],
            coverage_score=p["coverage_score"],
            playmaking_score=p["playmaking_score"],
        )
        for p in rankings
    ]


@router.get("/players/{player_id}", response_model=PlayerDetail)
async def get_player(player_id: int):
    """Get detailed information for a specific player."""
    rankings = get_cached_rankings()

    player = next((p for p in rankings if p["id"] == player_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    return PlayerDetail(
        id=player["id"],
        name=player["name"],
        team=player["team"],
        position=player["position"],
        games_played=player["games_played"],
        overall_score=player["overall_score"],
        run_defense_score=player["run_defense_score"],
        pass_rush_score=player["pass_rush_score"],
        coverage_score=player["coverage_score"],
        playmaking_score=player["playmaking_score"],
        stats=PlayerStats(**player["stats"]),
    )


@router.get("/compare", response_model=List[PlayerDetail])
async def compare_players(
    ids: str = Query(..., description="Comma-separated player IDs to compare"),
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

    rankings = get_cached_rankings()
    players = []

    for pid in player_ids:
        player = next((p for p in rankings if p["id"] == pid), None)
        if player:
            players.append(
                PlayerDetail(
                    id=player["id"],
                    name=player["name"],
                    team=player["team"],
                    position=player["position"],
                    games_played=player["games_played"],
                    overall_score=player["overall_score"],
                    run_defense_score=player["run_defense_score"],
                    pass_rush_score=player["pass_rush_score"],
                    coverage_score=player["coverage_score"],
                    playmaking_score=player["playmaking_score"],
                    stats=PlayerStats(**player["stats"]),
                )
            )

    if not players:
        raise HTTPException(status_code=404, detail="No players found with given IDs")

    return players


@router.post("/calculate", response_model=List[PlayerRanking])
async def calculate_rankings(
    weights: CategoryWeights = CategoryWeights(),
    min_games: int = Query(1, ge=1, le=17),
    position: Optional[str] = Query(None),
):
    """
    Calculate rankings with custom weights.

    Weights should sum to 1.0 for proper scaling.
    """
    weight_dict = {
        "run_defense": weights.run_defense,
        "pass_rush": weights.pass_rush,
        "coverage": weights.coverage,
        "playmaking": weights.playmaking,
    }

    rankings = process_player_rankings(
        min_games=min_games,
        position_filter=position,
        weights=weight_dict,
    )

    return [
        PlayerRanking(
            id=p["id"],
            name=p["name"],
            team=p["team"],
            position=p["position"],
            games_played=p["games_played"],
            overall_score=p["overall_score"],
            run_defense_score=p["run_defense_score"],
            pass_rush_score=p["pass_rush_score"],
            coverage_score=p["coverage_score"],
            playmaking_score=p["playmaking_score"],
        )
        for p in rankings
    ]

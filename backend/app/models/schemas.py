from typing import Optional

from pydantic import BaseModel


class PlayerStats(BaseModel):
    tackles: float = 0.0
    solo_tackles: float = 0.0
    assists: float = 0.0
    sacks: float = 0.0
    qb_hits: float = 0.0
    tackles_for_loss: float = 0.0
    passes_defended: float = 0.0
    interceptions: float = 0.0
    forced_fumbles: float = 0.0
    fumble_recoveries: float = 0.0
    defensive_tds: float = 0.0


class PlayerBase(BaseModel):
    name: str
    team: str
    position: str
    games_played: int


class PlayerRanking(PlayerBase):
    id: int
    overall_score: float
    run_defense_score: float
    pass_rush_score: float
    coverage_score: float
    playmaking_score: float


class PlayerDetail(PlayerRanking):
    stats: PlayerStats


class CategoryWeights(BaseModel):
    run_defense: float = 0.25
    pass_rush: float = 0.25
    coverage: float = 0.25
    playmaking: float = 0.25


class RankingRequest(BaseModel):
    weights: CategoryWeights = CategoryWeights()
    min_games: int = 1
    position: Optional[str] = None


class HealthResponse(BaseModel):
    status: str

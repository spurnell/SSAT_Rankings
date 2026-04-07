from typing import Optional, Dict, List, Any

from pydantic import BaseModel


class CategoryInfo(BaseModel):
    """Information about a ranking category."""
    id: str
    name: str
    stats: Optional[List[str]] = None


class PositionGroupInfo(BaseModel):
    """Information about a position group."""
    id: str
    name: str
    categories: List[CategoryInfo]
    sub_positions: Optional[List[str]] = None
    available_sources: Optional[List[str]] = None
    pff_categories: Optional[List[CategoryInfo]] = None
    pff_front7_categories: Optional[List[CategoryInfo]] = None
    pff_secondary_categories: Optional[List[CategoryInfo]] = None


class PlayerBase(BaseModel):
    """Base player information."""
    name: str
    team: str
    position: str
    games_played: int


class PlayerRanking(PlayerBase):
    """Player ranking with dynamic category scores."""
    id: int
    overall_score: float
    position_group: str = "DEF"
    category_scores: Dict[str, float]


class PlayerDetail(PlayerRanking):
    """Player with detailed stats."""
    stats: Dict[str, float]


class CategoryWeights(BaseModel):
    """Dynamic category weights."""
    weights: Dict[str, float] = {}


class RankingRequest(BaseModel):
    """Request for rankings with optional filters."""
    weights: Optional[Dict[str, float]] = None
    min_games: int = 1
    position: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str


# Legacy schemas for backward compatibility
class PlayerStats(BaseModel):
    """Legacy defensive player stats."""
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


class LegacyPlayerRanking(PlayerBase):
    """Legacy player ranking with fixed defensive category scores."""
    id: int
    overall_score: float
    run_defense_score: float
    pass_rush_score: float
    coverage_score: float
    playmaking_score: float


class LegacyPlayerDetail(LegacyPlayerRanking):
    """Legacy player detail with fixed stats."""
    stats: PlayerStats

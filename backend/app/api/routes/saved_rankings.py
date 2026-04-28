"""Saved custom rankings — CRUD + public share endpoint.

A saved ranking is a named, persisted version of the config the user tunes on
`/rankings/custom`. Share modes:
  - none:   private; not accessible via /api/shared/:slug
  - live:   public via /shared/:slug; results recomputed on each view
  - frozen: public via /shared/:slug; results snapshotted at save time and served verbatim

Compute reuses the same engine as /api/calculate (process_player_rankings /
process_pff_rankings) so there's one source of truth.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as OrmSession

from app.core.auth import get_current_user
from app.core.position_config import POSITION_GROUPS, get_pff_config
from app.db.database import get_db
from app.db.user_models import SavedRanking, User
from app.services.custom_categories import process_custom_category_rankings
from app.services.nfl_data_db import process_player_rankings
from app.services.pff_data import process_pff_rankings

router = APIRouter(tags=["saved-rankings"])


SHARE_MODES = {"none", "live", "frozen"}


# ---------- schemas ----------


class CustomCategoryStatPayload(BaseModel):
    source: str
    name: str


class CustomCategoryPayload(BaseModel):
    """A user-defined sub-category (mirrors CustomCategory in routes/rankings.py)."""
    id: str
    name: str
    weight: float = 1.0
    stats: List[CustomCategoryStatPayload]


class RankingConfig(BaseModel):
    """Shape of a saved ranking's configuration (the knobs on /rankings/custom).
    Mirrors CalculateRequest in routes/rankings.py."""
    position_group: str
    weights: Optional[Dict[str, float]] = None
    categories: Optional[List[CustomCategoryPayload]] = None
    min_games: int = 1
    position_filter: Optional[str] = None
    mode: Optional[str] = None
    min_seasons: Optional[int] = None
    source: Optional[str] = None


class SavedRankingCreate(RankingConfig):
    title: str = Field(min_length=1, max_length=200)
    share_mode: str = "none"


class SavedRankingUpdate(BaseModel):
    title: Optional[str] = None
    share_mode: Optional[str] = None
    weights: Optional[Dict[str, float]] = None
    categories: Optional[List[CustomCategoryPayload]] = None
    min_games: Optional[int] = None
    position_filter: Optional[str] = None
    mode: Optional[str] = None
    min_seasons: Optional[int] = None
    source: Optional[str] = None


class SavedRankingSummary(BaseModel):
    """Lightweight shape for list views."""
    id: int
    title: str
    position_group: str
    share_mode: str
    share_slug: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SavedRankingDetail(SavedRankingSummary):
    weights: Optional[Dict[str, float]] = None
    categories: Optional[List[Dict[str, Any]]] = None
    min_games: Optional[int] = None
    position_filter: Optional[str] = None
    mode: Optional[str] = None
    min_seasons: Optional[int] = None
    source: Optional[str] = None
    results: List[Dict[str, Any]]


class SharedRankingView(BaseModel):
    title: str
    position_group: str
    share_mode: str
    categories: Optional[List[Dict[str, Any]]] = None
    results: List[Dict[str, Any]]
    results_computed_at: Optional[datetime] = None


# ---------- helpers ----------


def _validate_share_mode(value: str) -> str:
    if value not in SHARE_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"share_mode must be one of {sorted(SHARE_MODES)}",
        )
    return value


def _validate_position_group(value: str) -> None:
    if value not in POSITION_GROUPS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid position_group: {value}",
        )


def _new_share_slug() -> str:
    return secrets.token_urlsafe(10)


def _compute_results(cfg: RankingConfig) -> List[Dict[str, Any]]:
    """Run the ranking engine. Returns plain dicts matching the /api/calculate
    response shape — safe to jsonify & cache in results_json."""
    if cfg.categories:
        return process_custom_category_rankings(
            position_group=cfg.position_group,
            custom_categories=[c.model_dump() for c in cfg.categories],
            min_games=cfg.min_games,
            position_filter=cfg.position_filter,
        )
    if cfg.source and cfg.source.startswith("pff") and get_pff_config(
        cfg.position_group, source=cfg.source
    ):
        return process_pff_rankings(
            position_group=cfg.position_group,
            min_games=cfg.min_games,
            weights=cfg.weights,
            position_filter=cfg.position_filter,
            source=cfg.source,
        )
    return process_player_rankings(
        min_games=cfg.min_games,
        position_filter=cfg.position_filter,
        weights=cfg.weights,
        position_group=cfg.position_group,
    )


def _config_from_row(row: SavedRanking) -> RankingConfig:
    """Reconstruct a RankingConfig from a stored SavedRanking row."""
    return RankingConfig(
        position_group=row.position_group,
        weights=row.weights,
        categories=row.categories,
        min_games=row.min_games or 1,
        position_filter=row.position_filter,
        mode=row.mode,
        min_seasons=row.min_seasons,
        source=row.source,
    )


def _detail_from_row(row: SavedRanking, results: List[Dict[str, Any]]) -> SavedRankingDetail:
    return SavedRankingDetail(
        id=row.id,
        title=row.title,
        position_group=row.position_group,
        share_mode=row.share_mode,
        share_slug=row.share_slug,
        created_at=row.created_at,
        updated_at=row.updated_at,
        weights=row.weights,
        categories=row.categories,
        min_games=row.min_games,
        position_filter=row.position_filter,
        mode=row.mode,
        min_seasons=row.min_seasons,
        source=row.source,
        results=results,
    )


# ---------- routes ----------


@router.post("/saved-rankings", response_model=SavedRankingDetail)
def create_saved_ranking(
    body: SavedRankingCreate,
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
) -> SavedRankingDetail:
    _validate_share_mode(body.share_mode)
    _validate_position_group(body.position_group)

    results: List[Dict[str, Any]] = []
    frozen_payload = None
    if body.share_mode == "frozen":
        results = _compute_results(body)
        frozen_payload = results

    share_slug = _new_share_slug() if body.share_mode != "none" else None

    row = SavedRanking(
        user_id=user.id,
        title=body.title,
        position_group=body.position_group,
        weights=body.weights,
        categories=[c.model_dump() for c in body.categories] if body.categories else None,
        min_games=body.min_games,
        mode=body.mode,
        min_seasons=body.min_seasons,
        position_filter=body.position_filter,
        source=body.source,
        share_mode=body.share_mode,
        share_slug=share_slug,
        results_json=frozen_payload,
        results_computed_at=datetime.now(timezone.utc) if frozen_payload is not None else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    if body.share_mode == "live":
        results = _compute_results(body)

    return _detail_from_row(row, results)


@router.get("/saved-rankings", response_model=List[SavedRankingSummary])
def list_saved_rankings(
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
) -> List[SavedRankingSummary]:
    rows = (
        db.query(SavedRanking)
        .filter(SavedRanking.user_id == user.id)
        .order_by(SavedRanking.updated_at.desc())
        .all()
    )
    return [SavedRankingSummary.model_validate(r) for r in rows]


@router.get("/saved-rankings/{ranking_id}", response_model=SavedRankingDetail)
def get_saved_ranking(
    ranking_id: int,
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
) -> SavedRankingDetail:
    row = (
        db.query(SavedRanking)
        .filter(SavedRanking.id == ranking_id, SavedRanking.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="not found")

    # Always recompute results for the owner so dashboard edits see fresh numbers.
    results = _compute_results(_config_from_row(row))
    return _detail_from_row(row, results)


@router.put("/saved-rankings/{ranking_id}", response_model=SavedRankingDetail)
def update_saved_ranking(
    ranking_id: int,
    body: SavedRankingUpdate,
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
) -> SavedRankingDetail:
    row = (
        db.query(SavedRanking)
        .filter(SavedRanking.id == ranking_id, SavedRanking.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="not found")

    if body.share_mode is not None:
        _validate_share_mode(body.share_mode)

    prev_share_mode = row.share_mode
    for field in (
        "title", "weights", "min_games", "mode", "min_seasons",
        "position_filter", "source", "share_mode",
    ):
        value = getattr(body, field)
        if value is not None:
            setattr(row, field, value)
    # categories needs explicit handling: model_dump on each entry, and we
    # allow callers to clear the field by sending an explicit empty list.
    if body.categories is not None:
        row.categories = [c.model_dump() for c in body.categories] or None

    # Slug lifecycle: generate on none→shared, clear on shared→none.
    if row.share_mode != "none" and not row.share_slug:
        row.share_slug = _new_share_slug()
    elif row.share_mode == "none":
        row.share_slug = None

    # Frozen results: snapshot if we transitioned into frozen (or refreshed config on a frozen).
    if row.share_mode == "frozen":
        row.results_json = _compute_results(_config_from_row(row))
        row.results_computed_at = datetime.now(timezone.utc)
    elif prev_share_mode == "frozen" and row.share_mode != "frozen":
        row.results_json = None
        row.results_computed_at = None

    db.commit()
    db.refresh(row)

    results = row.results_json if row.share_mode == "frozen" else _compute_results(_config_from_row(row))
    return _detail_from_row(row, results or [])


@router.delete("/saved-rankings/{ranking_id}")
def delete_saved_ranking(
    ranking_id: int,
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
) -> Dict[str, bool]:
    row = (
        db.query(SavedRanking)
        .filter(SavedRanking.id == ranking_id, SavedRanking.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/shared/{slug}", response_model=SharedRankingView)
def get_shared_ranking(
    slug: str,
    db: OrmSession = Depends(get_db),
) -> SharedRankingView:
    row = (
        db.query(SavedRanking)
        .filter(SavedRanking.share_slug == slug, SavedRanking.share_mode != "none")
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="not found")

    if row.share_mode == "frozen":
        results = row.results_json or []
    else:
        results = _compute_results(_config_from_row(row))

    return SharedRankingView(
        title=row.title,
        position_group=row.position_group,
        share_mode=row.share_mode,
        categories=row.categories,
        results=results,
        results_computed_at=row.results_computed_at,
    )

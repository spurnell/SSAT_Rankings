"""User-uploaded custom-data rankings — datasets, segments, rankings, sharing.

Distinct from `routes/saved_rankings.py` (which persists tuned configs of the
NFL ranking engine). Datasets, segments, and per-dataset rankings are
sport-agnostic — the user uploads CSV/XLSX files and configures categories
against their own columns.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as OrmSession

from app.core.auth import get_current_user
from app.db.custom_data_models import (
    CustomDataset,
    CustomDatasetRanking,
    DatasetRow,
    DatasetSegment,
)
from app.db.database import get_db
from app.db.user_models import User
from app.services.custom_data.file_parser import (
    ParseError,
    ParsedUpload,
    SchemaDrift,
    merge_schemas,
    parse_upload,
    reconcile_schemas,
)
from app.services.custom_data.ranking import (
    RankingComputeError,
    compute_dataset_ranking,
)


router = APIRouter(prefix="/custom-data", tags=["custom-data"])


SHARE_MODES = {"none", "live", "frozen"}
RANKING_MODES = {"single", "cumulative", "per_game"}
DRIFT_POLICIES = {"accept", "strict"}


# ---------- pydantic schemas ----------


class ColumnSchemaOut(BaseModel):
    name: str
    dtype: str


class SegmentSummary(BaseModel):
    id: int
    label: str
    source_filename: Optional[str]
    row_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class DatasetSummary(BaseModel):
    id: int
    title: str
    name_column: str
    segment_count: int
    total_rows: int
    created_at: datetime
    updated_at: datetime


class DatasetDetail(BaseModel):
    id: int
    title: str
    name_column: str
    column_schema: List[ColumnSchemaOut]
    segments: List[SegmentSummary]
    created_at: datetime
    updated_at: datetime


class SchemaDriftOut(BaseModel):
    added: List[ColumnSchemaOut] = []
    missing: List[str] = []
    type_mismatches: List[Dict[str, str]] = []


class SegmentUploadResponse(BaseModel):
    segment: SegmentSummary
    drift: SchemaDriftOut
    duplicates: List[str] = []


class RankingStatPayload(BaseModel):
    name: str
    lower_is_better: bool = False


class RankingCategoryPayload(BaseModel):
    id: str
    name: str
    weight: float = 1.0
    stats: List[RankingStatPayload]


class RankingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    categories: List[RankingCategoryPayload]
    mode: str = "single"
    segment_ids: List[int]
    games_column: Optional[str] = None
    min_rows: int = 1


class RankingUpdate(BaseModel):
    title: Optional[str] = None
    categories: Optional[List[RankingCategoryPayload]] = None
    mode: Optional[str] = None
    segment_ids: Optional[List[int]] = None
    games_column: Optional[str] = None
    min_rows: Optional[int] = None


class RankingShareUpdate(BaseModel):
    share_mode: str


class RankingSummary(BaseModel):
    id: int
    dataset_id: int
    title: str
    mode: str
    segment_ids: List[int]
    share_mode: str
    share_slug: Optional[str]
    created_at: datetime
    updated_at: datetime


class RankingDetail(RankingSummary):
    categories: List[Dict[str, Any]]
    games_column: Optional[str] = None
    min_rows: int
    results: List[Dict[str, Any]]


class SharedDatasetRankingView(BaseModel):
    title: str
    dataset_title: str
    mode: str
    share_mode: str
    categories: List[Dict[str, Any]]
    results: List[Dict[str, Any]]
    results_computed_at: Optional[datetime] = None


# ---------- helpers ----------


def _new_share_slug() -> str:
    return secrets.token_urlsafe(10)


def _validate_share_mode(value: str) -> str:
    if value not in SHARE_MODES:
        raise HTTPException(
            status_code=400, detail=f"share_mode must be one of {sorted(SHARE_MODES)}"
        )
    return value


def _validate_mode(value: str) -> str:
    if value not in RANKING_MODES:
        raise HTTPException(
            status_code=400, detail=f"mode must be one of {sorted(RANKING_MODES)}"
        )
    return value


def _drift_to_out(drift: SchemaDrift) -> SchemaDriftOut:
    return SchemaDriftOut(
        added=[ColumnSchemaOut(**c.as_dict()) for c in drift.added],
        missing=drift.missing,
        type_mismatches=drift.type_mismatches,
    )


def _segment_summary(seg: DatasetSegment) -> SegmentSummary:
    return SegmentSummary(
        id=seg.id,
        label=seg.label,
        source_filename=seg.source_filename,
        row_count=seg.row_count,
        created_at=seg.created_at,
    )


def _dataset_summary(ds: CustomDataset, segments: List[DatasetSegment]) -> DatasetSummary:
    return DatasetSummary(
        id=ds.id,
        title=ds.title,
        name_column=ds.name_column,
        segment_count=len(segments),
        total_rows=sum(s.row_count for s in segments),
        created_at=ds.created_at,
        updated_at=ds.updated_at,
    )


def _persist_segment(
    db: OrmSession,
    dataset: CustomDataset,
    label: str,
    filename: Optional[str],
    parsed: ParsedUpload,
    segment_schema: List[Dict[str, str]],
) -> DatasetSegment:
    """Create a DatasetSegment + all its DatasetRows in one transaction.
    Caller is responsible for db.commit().
    """
    seg = DatasetSegment(
        dataset_id=dataset.id,
        label=label,
        source_filename=filename,
        row_count=len(parsed.rows),
        segment_schema=segment_schema,
    )
    db.add(seg)
    db.flush()  # need seg.id for rows

    for parsed_row in parsed.rows:
        db.add(
            DatasetRow(
                dataset_id=dataset.id,
                segment_id=seg.id,
                entity_key=parsed_row.entity_key,
                entity_name=parsed_row.entity_name,
                data=parsed_row.data,
            )
        )
    return seg


def _load_dataset(
    db: OrmSession, dataset_id: int, user: User
) -> CustomDataset:
    ds = (
        db.query(CustomDataset)
        .filter(CustomDataset.id == dataset_id, CustomDataset.user_id == user.id)
        .first()
    )
    if not ds:
        raise HTTPException(status_code=404, detail="dataset not found")
    return ds


def _ranking_summary(r: CustomDatasetRanking) -> RankingSummary:
    return RankingSummary(
        id=r.id,
        dataset_id=r.dataset_id,
        title=r.title,
        mode=r.mode,
        segment_ids=list(r.segment_ids or []),
        share_mode=r.share_mode,
        share_slug=r.share_slug,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


def _ranking_detail(
    r: CustomDatasetRanking, results: List[Dict[str, Any]]
) -> RankingDetail:
    return RankingDetail(
        id=r.id,
        dataset_id=r.dataset_id,
        title=r.title,
        mode=r.mode,
        segment_ids=list(r.segment_ids or []),
        share_mode=r.share_mode,
        share_slug=r.share_slug,
        created_at=r.created_at,
        updated_at=r.updated_at,
        categories=list(r.categories or []),
        games_column=r.games_column,
        min_rows=r.min_rows or 1,
        results=results,
    )


def _safe_compute(
    db: OrmSession, dataset: CustomDataset, ranking: CustomDatasetRanking
) -> List[Dict[str, Any]]:
    try:
        return compute_dataset_ranking(db, dataset, ranking)
    except RankingComputeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------- dataset endpoints ----------


@router.post("/datasets", response_model=DatasetDetail)
async def create_dataset(
    file: UploadFile = File(...),
    title: str = Form(...),
    name_column: str = Form(...),
    segment_label: str = Form(...),
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
) -> DatasetDetail:
    """Create a new dataset from a fresh CSV/XLSX upload."""
    raw = await file.read()
    try:
        parsed = parse_upload(file.filename or "upload.csv", raw, name_column)
    except ParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    column_schema = [c.as_dict() for c in parsed.schema]
    ds = CustomDataset(
        user_id=user.id,
        title=title,
        name_column=name_column,
        column_schema=column_schema,
    )
    db.add(ds)
    db.flush()

    seg = _persist_segment(
        db,
        dataset=ds,
        label=segment_label,
        filename=file.filename,
        parsed=parsed,
        segment_schema=column_schema,
    )
    db.commit()
    db.refresh(ds)
    db.refresh(seg)

    return DatasetDetail(
        id=ds.id,
        title=ds.title,
        name_column=ds.name_column,
        column_schema=[ColumnSchemaOut(**c) for c in ds.column_schema],
        segments=[_segment_summary(seg)],
        created_at=ds.created_at,
        updated_at=ds.updated_at,
    )


@router.get("/datasets", response_model=List[DatasetSummary])
def list_datasets(
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
) -> List[DatasetSummary]:
    datasets = (
        db.query(CustomDataset)
        .filter(CustomDataset.user_id == user.id)
        .order_by(CustomDataset.updated_at.desc())
        .all()
    )
    return [_dataset_summary(ds, ds.segments) for ds in datasets]


@router.get("/datasets/{dataset_id}", response_model=DatasetDetail)
def get_dataset(
    dataset_id: int,
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
) -> DatasetDetail:
    ds = _load_dataset(db, dataset_id, user)
    return DatasetDetail(
        id=ds.id,
        title=ds.title,
        name_column=ds.name_column,
        column_schema=[ColumnSchemaOut(**c) for c in ds.column_schema],
        segments=[_segment_summary(s) for s in ds.segments],
        created_at=ds.created_at,
        updated_at=ds.updated_at,
    )


@router.get("/datasets/{dataset_id}/preview")
def preview_dataset(
    dataset_id: int,
    segment_id: int = Query(...),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
) -> Dict[str, Any]:
    ds = _load_dataset(db, dataset_id, user)
    rows = (
        db.query(DatasetRow)
        .filter(DatasetRow.dataset_id == ds.id, DatasetRow.segment_id == segment_id)
        .limit(limit)
        .all()
    )
    return {
        "rows": [
            {"entity_name": r.entity_name, "data": r.data} for r in rows
        ],
    }


@router.delete("/datasets/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
) -> Dict[str, bool]:
    ds = _load_dataset(db, dataset_id, user)
    db.delete(ds)
    db.commit()
    return {"ok": True}


# ---------- segment endpoints ----------


@router.post(
    "/datasets/{dataset_id}/segments", response_model=SegmentUploadResponse
)
async def append_segment(
    dataset_id: int,
    file: UploadFile = File(...),
    segment_label: str = Form(...),
    on_drift: str = Form("accept"),
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
) -> SegmentUploadResponse:
    if on_drift not in DRIFT_POLICIES:
        raise HTTPException(
            status_code=400,
            detail=f"on_drift must be one of {sorted(DRIFT_POLICIES)}",
        )

    ds = _load_dataset(db, dataset_id, user)

    # Idempotency: same label rejected so the client can prompt the user.
    existing = (
        db.query(DatasetSegment)
        .filter(
            DatasetSegment.dataset_id == ds.id,
            DatasetSegment.label == segment_label,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Segment '{segment_label}' already exists. Delete it first to replace.",
        )

    raw = await file.read()
    try:
        parsed = parse_upload(file.filename or "upload.csv", raw, ds.name_column)
    except ParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    drift = reconcile_schemas(ds.column_schema, parsed.schema)
    if drift.has_breaking_changes:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Type mismatch with existing dataset schema.",
                "type_mismatches": drift.type_mismatches,
            },
        )
    if on_drift == "strict" and not drift.is_empty:
        raise HTTPException(
            status_code=409,
            detail={"message": "Schema drift; re-submit with on_drift=accept.", **_drift_to_out(drift).model_dump()},
        )

    # Expand dataset schema with added columns (missing columns stay null per-row).
    if drift.added:
        ds.column_schema = merge_schemas(ds.column_schema, drift)

    segment_schema = [c.as_dict() for c in parsed.schema]
    seg = _persist_segment(
        db,
        dataset=ds,
        label=segment_label,
        filename=file.filename,
        parsed=parsed,
        segment_schema=segment_schema,
    )
    db.commit()
    db.refresh(seg)

    return SegmentUploadResponse(
        segment=_segment_summary(seg),
        drift=_drift_to_out(drift),
        duplicates=parsed.duplicate_entity_keys,
    )


@router.delete("/datasets/{dataset_id}/segments/{segment_id}")
def delete_segment(
    dataset_id: int,
    segment_id: int,
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
) -> Dict[str, bool]:
    ds = _load_dataset(db, dataset_id, user)
    seg = (
        db.query(DatasetSegment)
        .filter(DatasetSegment.id == segment_id, DatasetSegment.dataset_id == ds.id)
        .first()
    )
    if not seg:
        raise HTTPException(status_code=404, detail="segment not found")
    db.delete(seg)
    db.commit()
    return {"ok": True}


# ---------- ranking endpoints ----------


def _apply_ranking_payload(
    row: CustomDatasetRanking,
    *,
    title: Optional[str],
    categories: Optional[List[RankingCategoryPayload]],
    mode: Optional[str],
    segment_ids: Optional[List[int]],
    games_column: Optional[str],
    min_rows: Optional[int],
) -> None:
    if title is not None:
        row.title = title
    if categories is not None:
        row.categories = [c.model_dump() for c in categories]
    if mode is not None:
        _validate_mode(mode)
        row.mode = mode
    if segment_ids is not None:
        row.segment_ids = list(segment_ids)
    if games_column is not None:
        # empty string clears it
        row.games_column = games_column or None
    if min_rows is not None:
        row.min_rows = max(1, min_rows)


@router.post(
    "/datasets/{dataset_id}/rankings", response_model=RankingDetail
)
def create_ranking(
    dataset_id: int,
    body: RankingCreate,
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
) -> RankingDetail:
    ds = _load_dataset(db, dataset_id, user)
    _validate_mode(body.mode)

    row = CustomDatasetRanking(
        dataset_id=ds.id,
        user_id=user.id,
        title=body.title,
        categories=[c.model_dump() for c in body.categories],
        mode=body.mode,
        segment_ids=list(body.segment_ids),
        games_column=body.games_column or None,
        min_rows=max(1, body.min_rows or 1),
        share_mode="none",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    results = _safe_compute(db, ds, row)
    return _ranking_detail(row, results)


@router.get("/rankings", response_model=List[RankingSummary])
def list_rankings(
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
) -> List[RankingSummary]:
    rows = (
        db.query(CustomDatasetRanking)
        .filter(CustomDatasetRanking.user_id == user.id)
        .order_by(CustomDatasetRanking.updated_at.desc())
        .all()
    )
    return [_ranking_summary(r) for r in rows]


@router.get("/rankings/{ranking_id}", response_model=RankingDetail)
def get_ranking(
    ranking_id: int,
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
) -> RankingDetail:
    row = (
        db.query(CustomDatasetRanking)
        .filter(
            CustomDatasetRanking.id == ranking_id,
            CustomDatasetRanking.user_id == user.id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="ranking not found")
    ds = _load_dataset(db, row.dataset_id, user)
    results = _safe_compute(db, ds, row)
    return _ranking_detail(row, results)


@router.put("/rankings/{ranking_id}", response_model=RankingDetail)
def update_ranking(
    ranking_id: int,
    body: RankingUpdate,
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
) -> RankingDetail:
    row = (
        db.query(CustomDatasetRanking)
        .filter(
            CustomDatasetRanking.id == ranking_id,
            CustomDatasetRanking.user_id == user.id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="ranking not found")
    ds = _load_dataset(db, row.dataset_id, user)

    _apply_ranking_payload(
        row,
        title=body.title,
        categories=body.categories,
        mode=body.mode,
        segment_ids=body.segment_ids,
        games_column=body.games_column,
        min_rows=body.min_rows,
    )

    # Refresh frozen snapshot when config changes
    results = _safe_compute(db, ds, row)
    if row.share_mode == "frozen":
        row.results_json = results
        row.results_computed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(row)
    return _ranking_detail(row, results)


@router.delete("/rankings/{ranking_id}")
def delete_ranking(
    ranking_id: int,
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
) -> Dict[str, bool]:
    row = (
        db.query(CustomDatasetRanking)
        .filter(
            CustomDatasetRanking.id == ranking_id,
            CustomDatasetRanking.user_id == user.id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="ranking not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


# ---------- sharing ----------


@router.post("/rankings/{ranking_id}/share", response_model=RankingDetail)
def update_share_mode(
    ranking_id: int,
    body: RankingShareUpdate,
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
) -> RankingDetail:
    _validate_share_mode(body.share_mode)
    row = (
        db.query(CustomDatasetRanking)
        .filter(
            CustomDatasetRanking.id == ranking_id,
            CustomDatasetRanking.user_id == user.id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="ranking not found")
    ds = _load_dataset(db, row.dataset_id, user)

    prev_mode = row.share_mode
    row.share_mode = body.share_mode

    if row.share_mode != "none" and not row.share_slug:
        row.share_slug = _new_share_slug()
    elif row.share_mode == "none":
        row.share_slug = None

    results = _safe_compute(db, ds, row)
    if row.share_mode == "frozen":
        row.results_json = results
        row.results_computed_at = datetime.now(timezone.utc)
    elif prev_mode == "frozen" and row.share_mode != "frozen":
        row.results_json = None
        row.results_computed_at = None

    db.commit()
    db.refresh(row)
    return _ranking_detail(row, results)


@router.get("/shared/{slug}", response_model=SharedDatasetRankingView)
def get_shared(
    slug: str,
    db: OrmSession = Depends(get_db),
) -> SharedDatasetRankingView:
    row = (
        db.query(CustomDatasetRanking)
        .filter(
            CustomDatasetRanking.share_slug == slug,
            CustomDatasetRanking.share_mode != "none",
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="not found")

    ds = (
        db.query(CustomDataset)
        .filter(CustomDataset.id == row.dataset_id)
        .first()
    )
    if not ds:
        raise HTTPException(status_code=404, detail="not found")

    if row.share_mode == "frozen":
        results = row.results_json or []
    else:
        try:
            results = compute_dataset_ranking(db, ds, row)
        except RankingComputeError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    return SharedDatasetRankingView(
        title=row.title,
        dataset_title=ds.title,
        mode=row.mode,
        share_mode=row.share_mode,
        categories=list(row.categories or []),
        results=results,
        results_computed_at=row.results_computed_at,
    )

"""Compute rankings against user-uploaded datasets.

Reuses the z-score engine from `app.core.ranking` so the math matches the rest
of the site. Three aggregation modes:

  single      — one segment, rank rows as-is
  cumulative  — group by entity_key across the selected segments, sum numerics
  per_game    — cumulative, then divide every numeric stat by sum(games_column)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session as OrmSession

from app.core.ranking import (
    calculate_raw_category_z_scores,
    normalize_scores_to_range,
)
from app.db.custom_data_models import (
    CustomDataset,
    CustomDatasetRanking,
    DatasetRow,
    DatasetSegment,
)


class RankingComputeError(ValueError):
    """Surfaced to the API as HTTP 400."""


# Shape of a ranking category as stored on CustomDatasetRanking.categories:
#   {
#     "id": str,
#     "name": str,
#     "weight": float,
#     "stats": [{"name": str, "lower_is_better": bool}, ...]
#   }


def _numeric_columns(dataset: CustomDataset) -> Set[str]:
    return {c["name"] for c in dataset.column_schema if c["dtype"] == "numeric"}


def _coerce_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _aggregate_rows(
    rows: List[DatasetRow],
    mode: str,
    numeric_cols: Set[str],
    games_column: Optional[str],
    segments_by_id: Dict[int, DatasetSegment],
) -> List[Dict[str, Any]]:
    """Return one record per entity. Each record has:
        entity_key, entity_name, _games (optional), _segments, _stats
    where _stats is {col: float} for numeric columns referenced by the ranking.
    """
    if mode == "single":
        # One segment expected (validated upstream).
        records: List[Dict[str, Any]] = []
        for row in rows:
            stats = {
                col: (_coerce_number(row.data.get(col)) or 0.0) for col in numeric_cols
            }
            games_val: Optional[float] = None
            if games_column:
                games_val = _coerce_number(row.data.get(games_column))
            records.append(
                {
                    "entity_key": row.entity_key,
                    "entity_name": row.entity_name,
                    "_games": games_val,
                    "_segments": [segments_by_id[row.segment_id].label],
                    "_stats": stats,
                }
            )
        return records

    # cumulative + per_game both group by entity_key and sum numerics
    grouped: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        key = row.entity_key
        bucket = grouped.setdefault(
            key,
            {
                "entity_key": key,
                "entity_name": row.entity_name,
                "_games": 0.0 if games_column else None,
                "_segments": [],
                "_stats": {col: 0.0 for col in numeric_cols},
                "_has_games": False,
            },
        )
        # Keep the entity_name from the most recent segment.
        seg = segments_by_id.get(row.segment_id)
        if seg:
            bucket["_segments"].append(seg.label)
        bucket["entity_name"] = row.entity_name

        for col in numeric_cols:
            val = _coerce_number(row.data.get(col))
            if val is not None:
                bucket["_stats"][col] += val
        if games_column:
            g = _coerce_number(row.data.get(games_column))
            if g is not None:
                bucket["_games"] += g
                bucket["_has_games"] = True

    records = list(grouped.values())

    if mode == "per_game":
        if not games_column:
            raise RankingComputeError(
                "games_column is required for per_game mode."
            )
        for rec in records:
            games = rec["_games"]
            if not games or games <= 0:
                # Drop entities with no games — division would explode.
                rec["_skip"] = True
                continue
            rec["_stats"] = {
                col: (val / games) for col, val in rec["_stats"].items()
            }
        records = [r for r in records if not r.get("_skip")]

    return records


def compute_dataset_ranking(
    db: OrmSession,
    dataset: CustomDataset,
    ranking: CustomDatasetRanking,
) -> List[Dict[str, Any]]:
    """Compute the ranked results for a CustomDatasetRanking.

    The output shape matches what `process_custom_category_rankings` returns
    (overall_score, category_scores, stats) plus `contributing_segments`.
    """
    if ranking.mode not in ("single", "cumulative", "per_game"):
        raise RankingComputeError(f"Unknown mode: {ranking.mode}")

    segment_ids = list(ranking.segment_ids or [])
    if not segment_ids:
        raise RankingComputeError("At least one segment must be selected.")

    if ranking.mode == "single" and len(segment_ids) != 1:
        raise RankingComputeError(
            "single mode requires exactly one segment."
        )
    if ranking.mode == "per_game" and not ranking.games_column:
        raise RankingComputeError("per_game mode requires a games_column.")

    # Validate referenced segments belong to this dataset
    segments = (
        db.query(DatasetSegment)
        .filter(
            DatasetSegment.dataset_id == dataset.id,
            DatasetSegment.id.in_(segment_ids),
        )
        .all()
    )
    if len(segments) != len(segment_ids):
        raise RankingComputeError("One or more segment_ids are invalid for this dataset.")
    segments_by_id = {s.id: s for s in segments}

    # Determine which numeric columns we actually need (categories + games_col)
    referenced_cols: Set[str] = set()
    for cat in ranking.categories or []:
        for stat in cat.get("stats", []):
            name = stat.get("name") if isinstance(stat, dict) else None
            if name:
                referenced_cols.add(name)
    if ranking.games_column:
        referenced_cols.add(ranking.games_column)

    numeric_in_schema = _numeric_columns(dataset)
    needed_numerics = referenced_cols & numeric_in_schema
    if not needed_numerics:
        return []

    # Load rows
    rows = (
        db.query(DatasetRow)
        .filter(
            DatasetRow.dataset_id == dataset.id,
            DatasetRow.segment_id.in_(segment_ids),
        )
        .all()
    )
    if not rows:
        return []

    aggregated = _aggregate_rows(
        rows=rows,
        mode=ranking.mode,
        numeric_cols=needed_numerics,
        games_column=ranking.games_column,
        segments_by_id=segments_by_id,
    )

    # min_rows filter (counts contributing segments per entity).
    min_rows = ranking.min_rows or 1
    aggregated = [r for r in aggregated if len(r["_segments"]) >= min_rows]
    if not aggregated:
        return []

    # Build the synthetic category list expected by calculate_raw_category_z_scores.
    # Apply the lower_is_better sign flip on the raw values up-front (the engine
    # would otherwise consult a global LOWER_IS_BETTER_STATS set keyed by
    # NFL-specific stat names — see app/services/custom_categories.py:285-286).
    lower_is_better: Set[str] = set()
    synthetic_categories: List[Dict[str, Any]] = []
    weights_by_id: Dict[str, float] = {}
    for cat in ranking.categories or []:
        cat_id = str(cat.get("id") or cat.get("name") or "category")
        weights_by_id[cat_id] = float(cat.get("weight", 1.0) or 0.0)
        stat_names: List[str] = []
        for stat in cat.get("stats", []):
            name = stat.get("name") if isinstance(stat, dict) else None
            if not name or name not in needed_numerics:
                continue
            stat_names.append(name)
            if isinstance(stat, dict) and stat.get("lower_is_better"):
                lower_is_better.add(name)
        if not stat_names:
            continue
        synthetic_categories.append(
            {
                "id": cat_id,
                "name": str(cat.get("name") or cat_id),
                "weight": weights_by_id[cat_id],
                "stats": stat_names,
                "log_scale_stats": [],
            }
        )

    if not synthetic_categories:
        return []

    # Negate lower-is-better stats so high z-scores stay "good".
    for rec in aggregated:
        for col in lower_is_better:
            if col in rec["_stats"]:
                rec["_stats"][col] = -rec["_stats"][col]

    # Run the engine.
    all_stats = [rec["_stats"] for rec in aggregated]
    raw_category_scores = calculate_raw_category_z_scores(
        all_stats, synthetic_categories, set()
    )

    total_weight = sum(weights_by_id.get(c["id"], 0.0) for c in synthetic_categories)
    if total_weight <= 0:
        weights_norm = {
            c["id"]: 1.0 / len(synthetic_categories) for c in synthetic_categories
        }
    else:
        weights_norm = {
            c["id"]: weights_by_id.get(c["id"], 0.0) / total_weight
            for c in synthetic_categories
        }

    num_entities = len(aggregated)
    raw_overall = []
    for i in range(num_entities):
        v = sum(
            raw_category_scores[c["id"]][i] * weights_norm[c["id"]]
            for c in synthetic_categories
            if c["id"] in raw_category_scores
        )
        raw_overall.append(v)

    normalized_overall = normalize_scores_to_range(raw_overall)
    normalized_categories = {
        cid: normalize_scores_to_range(scores)
        for cid, scores in raw_category_scores.items()
    }

    results: List[Dict[str, Any]] = []
    for i, rec in enumerate(aggregated):
        # Undo the lower-is-better sign flip for display values.
        display_stats: Dict[str, float] = {}
        for col, val in rec["_stats"].items():
            display_stats[col] = -val if col in lower_is_better else val

        results.append(
            {
                "entity_key": rec["entity_key"],
                "entity_name": rec["entity_name"],
                "overall_score": round(normalized_overall[i], 1),
                "category_scores": {
                    c["id"]: round(normalized_categories[c["id"]][i], 1)
                    for c in synthetic_categories
                    if c["id"] in normalized_categories
                },
                "stats": {k: round(v, 3) for k, v in display_stats.items()},
                "contributing_segments": sorted(set(rec["_segments"])),
                "games": rec.get("_games"),
            }
        )

    results.sort(key=lambda r: r["overall_score"], reverse=True)
    return results

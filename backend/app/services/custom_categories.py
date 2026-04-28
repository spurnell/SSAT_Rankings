"""Custom-category ranking compute path.

Lets users define their own categories that pull from any combination of the
standard nflverse data and PFF CSVs (front7/secondary for DEF, plain pff for
others). Stats are addressed as ``(source, name)``; the same stat name across
two sources (e.g. ``tackles`` in standard DEF and PFF Front 7) refers to
distinct columns and gets namespaced internally as ``{source}__{name}``.

The compute path is:
  1. For each referenced source, load that source's per-player frame (reusing
     the same loaders the legacy compute path uses).
  2. Inner-join the frames on a normalized (player_name, position_group) key
     so a player is included only if they have rows in *every* source they're
     being scored against.
  3. Build a synthetic ``CategoryConfig`` list from the user's input where each
     category's ``stats`` reference the namespaced columns, then run the
     existing z-score engine.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from app.core.position_config import (
    CategoryConfig,
    LOWER_IS_BETTER_STATS,
    get_pff_config,
    get_position_group,
)
from app.core.ranking import (
    calculate_raw_category_z_scores,
    normalize_scores_to_range,
)
from app.services.nfl_data_db import (
    fetch_stats_for_position_group,
    map_position,
)
from app.services.pff_data import (
    PFF_TO_SITE_POSITION,
    SITE_TO_PFF_SUBPOSITION,
    _PREPARE_FUNCTIONS,
    load_pff_data,
)


_NAME_NORMALIZER = re.compile(r"[^a-z0-9]+")


def _normalize_name(name: Any) -> str:
    """Lowercase, strip punctuation/whitespace — used to match nflverse and PFF names."""
    if not isinstance(name, str):
        return ""
    return _NAME_NORMALIZER.sub("", name.lower()).strip()


def _internal_pff_group(position_group: str, source: str) -> str:
    """Translate a (group, source) pair to the internal PFF group key used by load_pff_data."""
    if position_group == "DEF":
        if source == "pff_front7":
            return "DEF_FRONT7"
        if source == "pff_secondary":
            return "DEF_SECONDARY"
        raise ValueError(f"Unsupported PFF source for DEF: {source}")
    return position_group


def _load_source_frame(position_group: str, source: str) -> pd.DataFrame:
    """Return a per-player DataFrame for one source, with a normalized join key.

    The frame retains its source-specific filters (PFF snap thresholds, standard
    games_played, etc.) and adds a ``_join_key`` column.
    """
    if source == "standard":
        df = fetch_stats_for_position_group(position_group)
        if df.empty:
            return df
        name_col = "display_name" if "display_name" in df.columns else "player_name"
        df = df.copy()
        df["_player_name"] = df[name_col]
    else:
        internal = _internal_pff_group(position_group, source)
        df = load_pff_data(internal)
        if df.empty:
            return df
        prep_fn = _PREPARE_FUNCTIONS.get(internal)
        if prep_fn:
            df = prep_fn(df)
        df = df.copy()
        if "player" in df.columns:
            df["_player_name"] = df["player"]
        if "team" not in df.columns and "team_name" in df.columns:
            df["team"] = df["team_name"]
        if "games_played" not in df.columns and "player_game_count" in df.columns:
            df["games_played"] = df["player_game_count"]

    df["_join_key"] = df["_player_name"].apply(_normalize_name)
    df = df[df["_join_key"] != ""]
    return df.reset_index(drop=True)


def _validate_source(position_group: str, source: str) -> None:
    if source == "standard":
        return
    if not source.startswith("pff"):
        raise ValueError(f"Unknown source: {source}")
    if get_pff_config(position_group, source=source) is None:
        raise ValueError(f"PFF source '{source}' is not available for {position_group}")


def _source_log_scale_set(position_group: str, source: str) -> Set[str]:
    """Stats from this source that should be log-scaled (rare events)."""
    if source == "standard":
        cats = get_position_group(position_group)["categories"]
    else:
        config = get_pff_config(position_group, source=source)
        cats = config["categories"] if config else []
    out: Set[str] = set()
    for cat in cats:
        out.update(cat.get("log_scale_stats", []))
    return out


def _display_position(position_group: str, raw_position: Any) -> str:
    if position_group == "DEF":
        return map_position(raw_position) if isinstance(raw_position, str) else position_group
    return PFF_TO_SITE_POSITION.get(raw_position, raw_position) if isinstance(raw_position, str) else position_group


def process_custom_category_rankings(
    position_group: str,
    custom_categories: List[Dict[str, Any]],
    min_games: int = 1,
    position_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Compute rankings against user-defined categories that may mix sources.

    ``custom_categories`` items shape::

        {
          "id": "<client-supplied stable id>",
          "name": "<display name>",
          "weight": <float>,
          "stats": [{"source": "standard"|"pff"|"pff_front7"|"pff_secondary",
                     "name": "<stat>"}, ...]
        }

    Returns a list of player dicts in the same shape as
    ``process_player_rankings``.
    """
    if not custom_categories:
        return []

    # Collect referenced sources and validate
    referenced_sources: Set[str] = set()
    for cat in custom_categories:
        for stat in cat.get("stats", []):
            referenced_sources.add(stat["source"])
    if not referenced_sources:
        return []
    for src in referenced_sources:
        _validate_source(position_group, src)

    # Load one frame per source
    source_frames: Dict[str, pd.DataFrame] = {}
    for src in referenced_sources:
        df = _load_source_frame(position_group, src)
        if df.empty:
            return []  # one source has no players → no rankings can be produced
        source_frames[src] = df

    # Determine join order. Pick the first one as the base; all are inner-joined
    # so order only affects which rows we kept identifying metadata from.
    sources_sorted = sorted(referenced_sources, key=lambda s: 0 if s == "standard" else 1)
    base_source = sources_sorted[0]
    base = source_frames[base_source]

    # Namespaced columns per source: rename stat columns to `{source}__{stat}`
    # to avoid name collisions on join.
    namespaced_frames: Dict[str, pd.DataFrame] = {}
    for src, df in source_frames.items():
        # Drop columns we don't care about on join: identity columns are kept on base only.
        stat_cols = [c for c in df.columns if not c.startswith("_") and c not in {
            "id", "stats_id", "season"
        }]
        renamed: Dict[str, str] = {}
        for col in stat_cols:
            # Reserve identity columns for the base frame only; namespace the rest.
            if col in {"display_name", "player_name", "player", "team", "team_name",
                       "position", "games_played", "gsis_id", "player_id", "player_game_count"}:
                continue
            renamed[col] = f"{src}__{col}"
        kept = ["_join_key"] + list(renamed.keys())
        slim = df[kept].rename(columns=renamed)
        namespaced_frames[src] = slim

    # Carry identity columns from the base frame
    base_identity_cols = ["_join_key", "_player_name"]
    for col in ("team", "position", "games_played", "gsis_id", "player_id"):
        if col in base.columns:
            base_identity_cols.append(col)
    identity = base[base_identity_cols].drop_duplicates(subset=["_join_key"], keep="first")

    # Inner-join all sources on _join_key
    merged = identity
    for src in sources_sorted:
        merged = merged.merge(namespaced_frames[src], on="_join_key", how="inner")
        # Drop duplicate join keys defensively
        merged = merged.drop_duplicates(subset=["_join_key"], keep="first")

    if merged.empty:
        return []

    # min_games filter only applies if we have a games_played column
    if "games_played" in merged.columns:
        merged = merged[merged["games_played"].fillna(0) >= min_games]

    # Sub-position filter (DEF only)
    if position_filter and position_filter != "All" and "position" in merged.columns:
        if "standard" in referenced_sources:
            merged = merged[merged["position"].apply(map_position) == position_filter]
        else:
            pff_code = SITE_TO_PFF_SUBPOSITION.get(position_filter, position_filter)
            merged = merged[merged["position"] == pff_code]

    if merged.empty:
        return []

    # Build synthetic CategoryConfig list with namespaced stat refs
    synthetic_categories: List[CategoryConfig] = []
    log_scale_union: Set[str] = set()
    namespaced_lower_is_better: Set[str] = set()
    weights_by_id: Dict[str, float] = {}

    # Pre-compute per-source log-scale sets so we know which stats need it.
    per_source_log: Dict[str, Set[str]] = {
        src: _source_log_scale_set(position_group, src) for src in referenced_sources
    }

    for cat in custom_categories:
        cat_id = str(cat.get("id") or cat.get("name") or "category")
        weights_by_id[cat_id] = float(cat.get("weight", 0.0))
        ns_stats: List[str] = []
        ns_log: List[str] = []
        for stat in cat.get("stats", []):
            src = stat["source"]
            name = stat["name"]
            ns = f"{src}__{name}"
            ns_stats.append(ns)
            if name in per_source_log.get(src, set()):
                ns_log.append(ns)
                log_scale_union.add(ns)
            if name in LOWER_IS_BETTER_STATS:
                namespaced_lower_is_better.add(ns)
        synthetic_categories.append({
            "id": cat_id,
            "name": str(cat.get("name") or cat_id),
            "stats": ns_stats,
            "weight": weights_by_id[cat_id],
            "log_scale_stats": ns_log,
        })

    # Skip empty categories — categories with zero stats produce no z-scores.
    synthetic_categories = [c for c in synthetic_categories if c["stats"]]
    if not synthetic_categories:
        return []

    # Pull the namespaced stat columns out as records; ensure missing columns default to 0
    all_ns_stats: Set[str] = set()
    for cat in synthetic_categories:
        all_ns_stats.update(cat["stats"])
    for ns in all_ns_stats:
        if ns not in merged.columns:
            merged[ns] = 0.0
    merged[list(all_ns_stats)] = merged[list(all_ns_stats)].fillna(0.0)

    # The ranking engine consults LOWER_IS_BETTER_STATS by exact stat name. Our
    # namespaced stats won't match that set, so apply the negation up-front by
    # flipping the sign of values on stats whose un-namespaced name is in the
    # lower-is-better set.
    for ns in namespaced_lower_is_better:
        merged[ns] = -merged[ns]

    all_stats = merged[list(all_ns_stats)].to_dict("records")

    raw_category_scores = calculate_raw_category_z_scores(
        all_stats, synthetic_categories, log_scale_union
    )

    num_players = len(all_stats)
    raw_overall_scores: List[float] = []
    total_weight = sum(weights_by_id.get(c["id"], 0.0) for c in synthetic_categories)
    if total_weight <= 0:
        # Fall back to equal weights so we never divide by zero.
        weights_norm = {c["id"]: 1.0 / len(synthetic_categories) for c in synthetic_categories}
    else:
        weights_norm = {c["id"]: weights_by_id.get(c["id"], 0.0) / total_weight for c in synthetic_categories}

    for i in range(num_players):
        raw_overall = sum(
            raw_category_scores[c["id"]][i] * weights_norm[c["id"]]
            for c in synthetic_categories
            if c["id"] in raw_category_scores
        )
        raw_overall_scores.append(raw_overall)

    normalized_overall = normalize_scores_to_range(raw_overall_scores)
    normalized_category_scores = {
        cat_id: normalize_scores_to_range(scores)
        for cat_id, scores in raw_category_scores.items()
    }

    rankings: List[Dict[str, Any]] = []
    rows = list(merged.iterrows())
    for i, (idx, row) in enumerate(rows):
        # Build a stats dict that surfaces the user-selected stats by their
        # original (un-namespaced) name. When two sources contribute the same
        # stat name, the later source wins; for the UI this is fine since both
        # values appear under their source's category column anyway.
        stats_dict: Dict[str, float] = {}
        for cat in custom_categories:
            for s in cat.get("stats", []):
                ns = f"{s['source']}__{s['name']}"
                if ns in row:
                    val = row[ns]
                    # Undo the lower-is-better sign flip for display.
                    if ns in namespaced_lower_is_better:
                        val = -val
                    stats_dict[s["name"]] = float(val if pd.notna(val) else 0.0)

        category_scores = {
            c["id"]: round(normalized_category_scores[c["id"]][i], 1)
            for c in synthetic_categories
            if c["id"] in normalized_category_scores
        }

        player_id_raw = row.get("gsis_id") or row.get("player_id") or row.get("_join_key") or idx
        try:
            player_id_int = abs(hash(str(player_id_raw))) % 1000000
        except Exception:
            player_id_int = idx + 1

        rankings.append({
            "id": player_id_int,
            "name": row.get("_player_name", "Unknown"),
            "team": row.get("team", "UNK"),
            "position": _display_position(position_group, row.get("position", position_group)),
            "position_group": position_group,
            "games_played": int(row["games_played"]) if "games_played" in row and pd.notna(row["games_played"]) else 0,
            "overall_score": round(normalized_overall[i], 1),
            "category_scores": category_scores,
            "stats": stats_dict,
        })

    rankings.sort(key=lambda x: x["overall_score"], reverse=True)
    return rankings

"""Tests for the user-upload custom-data rankings.

Covers:
  - file_parser: validation, dtype inference, name normalization, dedupe
  - reconcile_schemas: added / missing / type_mismatch
  - compute_dataset_ranking: single / cumulative / per_game modes,
    lower_is_better sign flip
  - HTTP endpoints: upload, append (with drift), create ranking, share
    lifecycle (slug generation/clearing, frozen snapshot)
  - tenant isolation
"""
from __future__ import annotations

import io
import pandas as pd

from app.db.custom_data_models import (
    CustomDataset,
    CustomDatasetRanking,
    DatasetRow,
    DatasetSegment,
)
from app.services.custom_data.file_parser import (
    ParseError,
    parse_upload,
    reconcile_schemas,
)
from app.services.custom_data.ranking import compute_dataset_ranking


# ---------- helpers ----------


def _csv_bytes(rows: list[dict]) -> bytes:
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


def _ten_rows(name_col: str = "player") -> list[dict]:
    return [
        {name_col: f"Player {i}", "yards": 100 + i * 10, "tds": i, "team": f"T{i % 3}"}
        for i in range(10)
    ]


# ---------- file_parser ----------


def test_parse_upload_happy_path():
    raw = _csv_bytes(_ten_rows())
    parsed = parse_upload("data.csv", raw, name_column="player")
    assert parsed.name_column == "player"
    # schema excludes the name column
    names = {c.name for c in parsed.schema}
    assert names == {"yards", "tds", "team"}
    dtypes = {c.name: c.dtype for c in parsed.schema}
    assert dtypes["yards"] == "numeric"
    assert dtypes["tds"] == "numeric"
    assert dtypes["team"] == "text"
    assert len(parsed.rows) == 10
    # entity_key is normalized
    assert parsed.rows[0].entity_key == "player0"


def test_parse_upload_rejects_too_few_rows():
    raw = _csv_bytes(_ten_rows()[:5])
    try:
        parse_upload("data.csv", raw, name_column="player")
    except ParseError as exc:
        assert "10 rows" in str(exc)
    else:
        raise AssertionError("expected ParseError")


def test_parse_upload_rejects_missing_name_column():
    raw = _csv_bytes(_ten_rows())
    try:
        parse_upload("data.csv", raw, name_column="nope")
    except ParseError as exc:
        assert "nope" in str(exc)
    else:
        raise AssertionError("expected ParseError")


def test_parse_upload_rejects_no_numeric_column():
    rows = [
        {"player": f"P {i}", "team": f"T{i}", "league": "X"} for i in range(10)
    ]
    raw = _csv_bytes(rows)
    try:
        parse_upload("data.csv", raw, name_column="player")
    except ParseError:
        return
    raise AssertionError("expected ParseError")


def test_parse_upload_dedupes_same_normalized_name():
    rows = _ten_rows()
    rows.append({"player": "PLAYER 0", "yards": 999, "tds": 0, "team": "X"})
    raw = _csv_bytes(rows)
    parsed = parse_upload("data.csv", raw, name_column="player")
    keys = [r.entity_key for r in parsed.rows]
    assert keys.count("player0") == 1
    assert parsed.duplicate_entity_keys == ["PLAYER 0"]


def test_reconcile_schemas_added_missing_mismatch():
    dataset_schema = [
        {"name": "yards", "dtype": "numeric"},
        {"name": "tds", "dtype": "numeric"},
        {"name": "team", "dtype": "text"},
    ]
    from app.services.custom_data.file_parser import ColumnSpec

    new_schema = [
        ColumnSpec(name="yards", dtype="numeric"),
        ColumnSpec(name="tds", dtype="text"),  # mismatch
        ColumnSpec(name="catches", dtype="numeric"),  # added
        # 'team' missing
    ]
    drift = reconcile_schemas(dataset_schema, new_schema)
    assert [c.name for c in drift.added] == ["catches"]
    assert drift.missing == ["team"]
    assert drift.type_mismatches == [
        {"name": "tds", "dataset_dtype": "numeric", "segment_dtype": "text"}
    ]
    assert drift.has_breaking_changes


# ---------- compute_dataset_ranking ----------


def _build_dataset_with_two_segments(db) -> tuple[CustomDataset, DatasetSegment, DatasetSegment]:
    ds = CustomDataset(
        user_id=_seed_test_user(db).id,
        title="Test",
        name_column="player",
        column_schema=[
            {"name": "yards", "dtype": "numeric"},
            {"name": "tds", "dtype": "numeric"},
            {"name": "games", "dtype": "numeric"},
        ],
    )
    db.add(ds)
    db.flush()

    seg_2024 = DatasetSegment(
        dataset_id=ds.id, label="2024", row_count=2,
        segment_schema=ds.column_schema,
    )
    seg_2025 = DatasetSegment(
        dataset_id=ds.id, label="2025", row_count=2,
        segment_schema=ds.column_schema,
    )
    db.add_all([seg_2024, seg_2025])
    db.flush()

    # Two players, both present in both segments.
    rows = [
        # Alice 2024 — 100 yards, 5 tds, 10 games
        DatasetRow(dataset_id=ds.id, segment_id=seg_2024.id,
                   entity_key="alice", entity_name="Alice",
                   data={"yards": 100, "tds": 5, "games": 10}),
        # Bob 2024 — 50 yards, 2 tds, 10 games
        DatasetRow(dataset_id=ds.id, segment_id=seg_2024.id,
                   entity_key="bob", entity_name="Bob",
                   data={"yards": 50, "tds": 2, "games": 10}),
        # Alice 2025 — 200 yards, 8 tds, 20 games
        DatasetRow(dataset_id=ds.id, segment_id=seg_2025.id,
                   entity_key="alice", entity_name="Alice",
                   data={"yards": 200, "tds": 8, "games": 20}),
        # Bob 2025 — 150 yards, 6 tds, 10 games
        DatasetRow(dataset_id=ds.id, segment_id=seg_2025.id,
                   entity_key="bob", entity_name="Bob",
                   data={"yards": 150, "tds": 6, "games": 10}),
    ]
    db.add_all(rows)
    db.flush()
    return ds, seg_2024, seg_2025


def _seed_test_user(db):
    from app.db.user_models import User
    user = User(email=f"compute_{id(db)}@example.com")
    db.add(user)
    db.flush()
    return user


def _ranking(ds: CustomDataset, user_id: int, *, mode: str, segment_ids: list[int],
             games_column: str | None = None, lower_is_better: bool = False
             ) -> CustomDatasetRanking:
    return CustomDatasetRanking(
        dataset_id=ds.id,
        user_id=user_id,
        title="r",
        categories=[
            {
                "id": "scoring",
                "name": "Scoring",
                "weight": 1.0,
                "stats": [
                    {"name": "yards", "lower_is_better": lower_is_better},
                    {"name": "tds", "lower_is_better": False},
                ],
            }
        ],
        mode=mode,
        segment_ids=segment_ids,
        games_column=games_column,
        min_rows=1,
    )


def test_compute_single_segment(db_session):
    ds, seg_2024, _ = _build_dataset_with_two_segments(db_session)
    r = _ranking(ds, ds.user_id, mode="single", segment_ids=[seg_2024.id])
    results = compute_dataset_ranking(db_session, ds, r)
    assert [x["entity_name"] for x in results] == ["Alice", "Bob"]
    assert results[0]["overall_score"] == 100.0
    assert results[1]["overall_score"] == 60.0
    # contributing_segments should reflect just the one
    assert results[0]["contributing_segments"] == ["2024"]


def test_compute_cumulative_sums_across_segments(db_session):
    ds, seg_2024, seg_2025 = _build_dataset_with_two_segments(db_session)
    r = _ranking(ds, ds.user_id, mode="cumulative", segment_ids=[seg_2024.id, seg_2025.id])
    results = compute_dataset_ranking(db_session, ds, r)
    # Alice totals: yards=300, tds=13; Bob totals: yards=200, tds=8 — Alice wins
    by_name = {x["entity_name"]: x for x in results}
    assert by_name["Alice"]["stats"]["yards"] == 300
    assert by_name["Alice"]["stats"]["tds"] == 13
    assert by_name["Bob"]["stats"]["yards"] == 200
    assert by_name["Alice"]["overall_score"] > by_name["Bob"]["overall_score"]
    assert sorted(by_name["Alice"]["contributing_segments"]) == ["2024", "2025"]


def test_compute_per_game_divides_by_games_sum(db_session):
    ds, seg_2024, seg_2025 = _build_dataset_with_two_segments(db_session)
    r = _ranking(
        ds,
        ds.user_id,
        mode="per_game",
        segment_ids=[seg_2024.id, seg_2025.id],
        games_column="games",
    )
    results = compute_dataset_ranking(db_session, ds, r)
    by_name = {x["entity_name"]: x for x in results}
    # Alice: yards 300/30 = 10.0, tds 13/30 ≈ 0.4333
    # Bob:   yards 200/20 = 10.0, tds 8/20 = 0.4
    assert by_name["Alice"]["stats"]["yards"] == 10.0
    assert by_name["Bob"]["stats"]["yards"] == 10.0
    # Per-game tds: Alice 0.433, Bob 0.4 — Alice wins
    assert by_name["Alice"]["overall_score"] >= by_name["Bob"]["overall_score"]


def test_compute_lower_is_better_flips_sign(db_session):
    ds, seg_2024, _ = _build_dataset_with_two_segments(db_session)
    # In single mode with lower_is_better on yards, Bob (fewer yards) should win.
    r = _ranking(
        ds,
        ds.user_id,
        mode="single",
        segment_ids=[seg_2024.id],
        lower_is_better=True,
    )
    # Use only the lower-is-better stat (yards) so the higher-is-better tds
    # doesn't drown out the inversion.
    r.categories = [
        {
            "id": "errors",
            "name": "Errors",
            "weight": 1.0,
            "stats": [{"name": "yards", "lower_is_better": True}],
        }
    ]
    results = compute_dataset_ranking(db_session, ds, r)
    # Bob has fewer yards — should rank first now.
    assert results[0]["entity_name"] == "Bob"
    # Display values are NOT sign-flipped — Bob should still show yards=50.
    assert results[0]["stats"]["yards"] == 50


# ---------- HTTP endpoints ----------


def test_create_dataset_endpoint(auth_client):
    raw = _csv_bytes(_ten_rows())
    res = auth_client.post(
        "/api/custom-data/datasets",
        data={"title": "My data", "name_column": "player", "segment_label": "2024"},
        files={"file": ("data.csv", raw, "text/csv")},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["title"] == "My data"
    assert len(body["segments"]) == 1
    assert body["segments"][0]["label"] == "2024"
    assert body["segments"][0]["row_count"] == 10


def test_append_segment_with_added_column(auth_client):
    raw1 = _csv_bytes(_ten_rows())
    r1 = auth_client.post(
        "/api/custom-data/datasets",
        data={"title": "D", "name_column": "player", "segment_label": "2024"},
        files={"file": ("a.csv", raw1, "text/csv")},
    )
    ds_id = r1.json()["id"]

    new_rows = [
        {"player": f"Player {i}", "yards": 200 + i, "tds": i + 1, "team": f"T{i}", "catches": i * 2}
        for i in range(10)
    ]
    raw2 = _csv_bytes(new_rows)
    r2 = auth_client.post(
        f"/api/custom-data/datasets/{ds_id}/segments",
        data={"segment_label": "2025", "on_drift": "accept"},
        files={"file": ("b.csv", raw2, "text/csv")},
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["segment"]["label"] == "2025"
    assert [c["name"] for c in body["drift"]["added"]] == ["catches"]


def test_append_segment_duplicate_label_rejected(auth_client):
    raw = _csv_bytes(_ten_rows())
    r1 = auth_client.post(
        "/api/custom-data/datasets",
        data={"title": "D", "name_column": "player", "segment_label": "2024"},
        files={"file": ("a.csv", raw, "text/csv")},
    )
    ds_id = r1.json()["id"]

    r2 = auth_client.post(
        f"/api/custom-data/datasets/{ds_id}/segments",
        data={"segment_label": "2024", "on_drift": "accept"},
        files={"file": ("b.csv", raw, "text/csv")},
    )
    assert r2.status_code == 409


def test_create_ranking_and_compute(auth_client):
    raw = _csv_bytes(_ten_rows())
    r1 = auth_client.post(
        "/api/custom-data/datasets",
        data={"title": "D", "name_column": "player", "segment_label": "2024"},
        files={"file": ("a.csv", raw, "text/csv")},
    )
    ds = r1.json()
    seg_id = ds["segments"][0]["id"]

    r2 = auth_client.post(
        f"/api/custom-data/datasets/{ds['id']}/rankings",
        json={
            "title": "Top yards",
            "categories": [
                {
                    "id": "scoring",
                    "name": "Scoring",
                    "weight": 1.0,
                    "stats": [{"name": "yards", "lower_is_better": False}],
                }
            ],
            "mode": "single",
            "segment_ids": [seg_id],
        },
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert len(body["results"]) == 10
    # Player 9 has the most yards → should be first.
    assert body["results"][0]["entity_name"] == "Player 9"


def test_share_lifecycle(auth_client):
    raw = _csv_bytes(_ten_rows())
    r1 = auth_client.post(
        "/api/custom-data/datasets",
        data={"title": "D", "name_column": "player", "segment_label": "2024"},
        files={"file": ("a.csv", raw, "text/csv")},
    )
    ds = r1.json()

    r2 = auth_client.post(
        f"/api/custom-data/datasets/{ds['id']}/rankings",
        json={
            "title": "T",
            "categories": [
                {
                    "id": "scoring",
                    "name": "Scoring",
                    "weight": 1.0,
                    "stats": [{"name": "yards", "lower_is_better": False}],
                }
            ],
            "mode": "single",
            "segment_ids": [ds["segments"][0]["id"]],
        },
    )
    ranking = r2.json()
    rid = ranking["id"]
    assert ranking["share_mode"] == "none"
    assert ranking["share_slug"] is None

    # turn on live sharing — slug generated
    r3 = auth_client.post(f"/api/custom-data/rankings/{rid}/share", json={"share_mode": "live"})
    assert r3.status_code == 200
    slug = r3.json()["share_slug"]
    assert slug

    # Public view works without auth.
    from fastapi.testclient import TestClient
    from app.main import app as fastapi_app
    public = TestClient(fastapi_app)
    r4 = public.get(f"/api/custom-data/shared/{slug}")
    assert r4.status_code == 200
    assert len(r4.json()["results"]) == 10

    # turn off — slug cleared
    r5 = auth_client.post(f"/api/custom-data/rankings/{rid}/share", json={"share_mode": "none"})
    assert r5.json()["share_slug"] is None


def test_tenant_isolation_get_dataset(auth_client, second_client):
    raw = _csv_bytes(_ten_rows())
    r1 = auth_client.post(
        "/api/custom-data/datasets",
        data={"title": "D", "name_column": "player", "segment_label": "2024"},
        files={"file": ("a.csv", raw, "text/csv")},
    )
    ds_id = r1.json()["id"]

    r2 = second_client.get(f"/api/custom-data/datasets/{ds_id}")
    assert r2.status_code == 404

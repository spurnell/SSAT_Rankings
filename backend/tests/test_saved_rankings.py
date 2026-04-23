"""Tests for /api/saved-rankings/* and /api/shared/:slug."""
from __future__ import annotations

from typing import Any, Dict

import pytest

from app.db.user_models import SavedRanking


DEF_WEIGHTS = {
    "run_defense": 0.25, "pass_rush": 0.25, "coverage": 0.25, "playmaking": 0.25,
}


def _base_body(**overrides: Any) -> Dict[str, Any]:
    body = {
        "title": "My ranking",
        "share_mode": "none",
        "position_group": "DEF",
        "weights": DEF_WEIGHTS,
        "min_games": 1,
    }
    body.update(overrides)
    return body


# ---------------- POST /api/saved-rankings ----------------


def test_create_requires_auth(client):
    r = client.post("/api/saved-rankings", json=_base_body())
    assert r.status_code == 401


def test_create_private_no_slug_no_compute(auth_client, mock_rankings_compute):
    r = auth_client.post("/api/saved-rankings", json=_base_body(share_mode="none"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["share_mode"] == "none"
    assert body["share_slug"] is None
    assert body["results"] == []
    # Private saves don't call the compute engine
    assert mock_rankings_compute.call_count == 0


def test_create_live_generates_slug_and_results(auth_client, mock_rankings_compute):
    r = auth_client.post("/api/saved-rankings", json=_base_body(share_mode="live"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["share_mode"] == "live"
    assert body["share_slug"] is not None
    assert len(body["results"]) == 3  # stub returns 3
    assert mock_rankings_compute.call_count == 1


def test_create_frozen_snapshots_results(auth_client, db_session, mock_rankings_compute):
    r = auth_client.post("/api/saved-rankings", json=_base_body(share_mode="frozen"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["share_mode"] == "frozen"
    assert body["share_slug"] is not None

    # results_json persisted
    row = db_session.query(SavedRanking).filter(SavedRanking.id == body["id"]).one()
    assert row.results_json is not None
    assert len(row.results_json) == 3
    assert row.results_computed_at is not None


def test_create_invalid_share_mode(auth_client):
    r = auth_client.post("/api/saved-rankings", json=_base_body(share_mode="bogus"))
    assert r.status_code == 400


def test_create_invalid_position_group(auth_client):
    r = auth_client.post("/api/saved-rankings", json=_base_body(position_group="NOPE"))
    assert r.status_code == 400


# ---------------- GET /api/saved-rankings (list) ----------------


def test_list_returns_only_own_rankings(auth_client, second_client, db_session):
    # auth_client saves two; second_client saves one
    auth_client.post("/api/saved-rankings", json=_base_body(title="mine-A"))
    auth_client.post("/api/saved-rankings", json=_base_body(title="mine-B"))
    second_client.post("/api/saved-rankings", json=_base_body(title="theirs"))

    r1 = auth_client.get("/api/saved-rankings")
    titles1 = {row["title"] for row in r1.json()}
    assert titles1 == {"mine-A", "mine-B"}

    r2 = second_client.get("/api/saved-rankings")
    titles2 = {row["title"] for row in r2.json()}
    assert titles2 == {"theirs"}


# ---------------- GET /api/saved-rankings/{id} ----------------


def test_get_own_ranking_recomputes(auth_client, mock_rankings_compute):
    create = auth_client.post("/api/saved-rankings", json=_base_body(share_mode="none"))
    rid = create.json()["id"]
    mock_rankings_compute.reset_mock()

    r = auth_client.get(f"/api/saved-rankings/{rid}")
    assert r.status_code == 200
    assert len(r.json()["results"]) == 3
    assert mock_rankings_compute.call_count == 1


def test_get_other_users_ranking_404(auth_client, second_client):
    create = second_client.post("/api/saved-rankings", json=_base_body(title="theirs"))
    rid = create.json()["id"]

    r = auth_client.get(f"/api/saved-rankings/{rid}")
    assert r.status_code == 404


# ---------------- PUT /api/saved-rankings/{id} ----------------


def test_update_title(auth_client, db_session):
    create = auth_client.post("/api/saved-rankings", json=_base_body(title="before"))
    rid = create.json()["id"]

    r = auth_client.put(f"/api/saved-rankings/{rid}", json={"title": "after"})
    assert r.status_code == 200
    assert r.json()["title"] == "after"


def test_update_none_to_live_generates_slug(auth_client):
    create = auth_client.post("/api/saved-rankings", json=_base_body(share_mode="none"))
    rid = create.json()["id"]
    assert create.json()["share_slug"] is None

    r = auth_client.put(f"/api/saved-rankings/{rid}", json={"share_mode": "live"})
    assert r.status_code == 200
    assert r.json()["share_slug"] is not None
    assert r.json()["share_mode"] == "live"


def test_update_live_to_none_clears_slug(auth_client, db_session):
    create = auth_client.post("/api/saved-rankings", json=_base_body(share_mode="live"))
    rid = create.json()["id"]

    r = auth_client.put(f"/api/saved-rankings/{rid}", json={"share_mode": "none"})
    assert r.status_code == 200
    assert r.json()["share_slug"] is None

    row = db_session.query(SavedRanking).filter(SavedRanking.id == rid).one()
    assert row.share_slug is None


def test_update_to_frozen_populates_results_json(auth_client, db_session):
    create = auth_client.post("/api/saved-rankings", json=_base_body(share_mode="live"))
    rid = create.json()["id"]

    r = auth_client.put(f"/api/saved-rankings/{rid}", json={"share_mode": "frozen"})
    assert r.status_code == 200

    row = db_session.query(SavedRanking).filter(SavedRanking.id == rid).one()
    assert row.share_mode == "frozen"
    assert row.results_json is not None
    assert len(row.results_json) == 3


def test_update_frozen_to_live_clears_results_json(auth_client, db_session):
    create = auth_client.post("/api/saved-rankings", json=_base_body(share_mode="frozen"))
    rid = create.json()["id"]

    r = auth_client.put(f"/api/saved-rankings/{rid}", json={"share_mode": "live"})
    assert r.status_code == 200

    row = db_session.query(SavedRanking).filter(SavedRanking.id == rid).one()
    assert row.share_mode == "live"
    assert row.results_json is None


def test_update_other_users_ranking_404(auth_client, second_client):
    create = second_client.post("/api/saved-rankings", json=_base_body())
    rid = create.json()["id"]

    r = auth_client.put(f"/api/saved-rankings/{rid}", json={"title": "hacked"})
    assert r.status_code == 404


# ---------------- DELETE /api/saved-rankings/{id} ----------------


def test_delete_own_ranking(auth_client, db_session):
    create = auth_client.post("/api/saved-rankings", json=_base_body())
    rid = create.json()["id"]

    r = auth_client.delete(f"/api/saved-rankings/{rid}")
    assert r.status_code == 200
    assert r.json() == {"ok": True}

    assert db_session.query(SavedRanking).filter(SavedRanking.id == rid).count() == 0


def test_delete_other_users_ranking_404(auth_client, second_client, db_session):
    create = second_client.post("/api/saved-rankings", json=_base_body())
    rid = create.json()["id"]

    r = auth_client.delete(f"/api/saved-rankings/{rid}")
    assert r.status_code == 404

    # Row is still there
    assert db_session.query(SavedRanking).filter(SavedRanking.id == rid).count() == 1


# ---------------- GET /api/shared/{slug} ----------------


def test_shared_live_recomputes_each_view(auth_client, client, mock_rankings_compute):
    create = auth_client.post("/api/saved-rankings", json=_base_body(share_mode="live"))
    slug = create.json()["share_slug"]

    mock_rankings_compute.reset_mock()
    r = client.get(f"/api/shared/{slug}")  # note: client without auth cookie
    assert r.status_code == 200
    assert r.json()["share_mode"] == "live"
    assert len(r.json()["results"]) == 3
    assert mock_rankings_compute.call_count == 1

    # Second view recomputes again
    r2 = client.get(f"/api/shared/{slug}")
    assert r2.status_code == 200
    assert mock_rankings_compute.call_count == 2


def test_shared_frozen_uses_cache_no_compute(auth_client, client, mock_rankings_compute):
    create = auth_client.post("/api/saved-rankings", json=_base_body(share_mode="frozen"))
    slug = create.json()["share_slug"]

    mock_rankings_compute.reset_mock()
    r = client.get(f"/api/shared/{slug}")
    assert r.status_code == 200
    assert r.json()["share_mode"] == "frozen"
    assert len(r.json()["results"]) == 3
    # Frozen must NOT hit the compute engine
    assert mock_rankings_compute.call_count == 0


def test_shared_private_ranking_slug_404(auth_client, client, db_session):
    # Manually create a row with share_mode='none' but a non-null slug
    # (shouldn't happen normally, but the route should still refuse it).
    create = auth_client.post("/api/saved-rankings", json=_base_body(share_mode="live"))
    rid = create.json()["id"]
    slug = create.json()["share_slug"]

    row = db_session.query(SavedRanking).filter(SavedRanking.id == rid).one()
    row.share_mode = "none"
    db_session.flush()

    r = client.get(f"/api/shared/{slug}")
    assert r.status_code == 404


def test_shared_unknown_slug_404(client):
    r = client.get("/api/shared/definitely-not-a-real-slug")
    assert r.status_code == 404

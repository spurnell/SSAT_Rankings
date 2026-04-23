"""One-shot: copy rows from the legacy SQLite files (blog.db + rankings.db)
into the Postgres pointed at by DATABASE_URL. Idempotent — skips existing PKs.

Usage (from backend/):
    python scripts/migrate_sqlite_to_postgres.py
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Iterable

from sqlalchemy import text

from app.db.database import SessionLocal

# SQLite → Postgres type coercion rules. SQLite is type-loose (bools are 0/1,
# JSON is stored as text), but Postgres enforces column types strictly.
BOOL_COLS = {"blog_posts": {"is_published"}}
JSON_COLS = {"blog_posts": {"featured_players", "tags"}}


def _coerce_row(table: str, row: dict) -> dict:
    for col in BOOL_COLS.get(table, ()):
        if col in row and row[col] is not None and not isinstance(row[col], bool):
            row[col] = bool(row[col])
    for col in JSON_COLS.get(table, ()):
        v = row.get(col)
        if v is None:
            continue
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                row[col] = None
                continue
            # Normalize: store the JSON-encoded string, not the Python obj —
            # psycopg v3 handles list/dict→jsonb natively only when the column
            # is typed, so we go through raw JSON text via the column's JSON type.
            row[col] = json.dumps(parsed) if parsed is not None else None
        elif isinstance(v, (list, dict)):
            row[col] = json.dumps(v)
    return row

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BLOG_DB = BACKEND_ROOT / "data" / "blog.db"
DEFAULT_RANKINGS_DB = BACKEND_ROOT / "data" / "rankings.db"
BATCH_SIZE = 500


def _sqlite_conn(path: Path) -> sqlite3.Connection | None:
    if not path.exists():
        print(f"[skip] {path} does not exist")
        return None
    # read-only
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _chunked(rows: Iterable[dict], size: int) -> Iterable[list[dict]]:
    batch: list[dict] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def _copy_table(
    sqlite_conn: sqlite3.Connection,
    table: str,
    columns: list[str],
    pk: str,
) -> int:
    """Copy rows from a SQLite table into Postgres via SQLAlchemy, skipping
    existing PKs. Returns the number of rows inserted."""
    placeholders = ", ".join(f":{c}" for c in columns)
    col_list = ", ".join(columns)
    insert_sql = text(
        f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
        f"ON CONFLICT ({pk}) DO NOTHING"
    )

    cursor = sqlite_conn.execute(f"SELECT {col_list} FROM {table}")
    row_iter = (_coerce_row(table, {c: row[c] for c in columns}) for row in cursor)

    inserted = 0
    with SessionLocal() as session:
        for batch in _chunked(row_iter, BATCH_SIZE):
            result = session.execute(insert_sql, batch)
            session.commit()
            # rowcount is -1 for ON CONFLICT in some drivers; fall back to batch size
            inserted += result.rowcount if result.rowcount and result.rowcount > 0 else len(batch)
    print(f"[ok] {table}: processed {inserted} rows")
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blog-db", type=Path, default=DEFAULT_BLOG_DB)
    parser.add_argument("--rankings-db", type=Path, default=DEFAULT_RANKINGS_DB)
    args = parser.parse_args()

    blog = _sqlite_conn(args.blog_db)
    if blog is not None:
        _copy_table(
            blog,
            "blog_posts",
            [
                "id", "slug", "title", "excerpt", "content", "post_type",
                "featured_players", "tags", "published_at", "created_at",
                "is_published",
            ],
            pk="id",
        )
        blog.close()

    rankings = _sqlite_conn(args.rankings_db)
    if rankings is not None:
        _copy_table(
            rankings,
            "players",
            ["gsis_id", "display_name", "position", "position_group", "team", "headshot_url"],
            pk="gsis_id",
        )
        _copy_table(
            rankings,
            "player_season_stats",
            [
                "id", "gsis_id", "season", "team", "games_played",
                "completions", "attempts", "passing_yards", "passing_tds",
                "interceptions", "sacks", "sack_yards", "passing_first_downs",
                "sack_fumbles",
                "carries", "rushing_yards", "rushing_tds", "rushing_first_downs",
                "rushing_fumbles", "longest_rush",
                "receptions", "targets", "receiving_yards", "receiving_tds",
                "receiving_fumbles", "receiving_first_downs",
                "receiving_yards_after_catch", "longest_reception",
                "tackles", "solo_tackles", "assists", "def_sacks", "qb_hits",
                "tackles_for_loss", "passes_defended", "def_interceptions",
                "forced_fumbles", "fumble_recoveries", "defensive_tds",
                "fg_made", "fg_attempts", "fg_made_40_49", "fg_made_50_plus",
                "long_fg", "xp_made", "xp_attempts", "kicking_points",
                "updated_at",
            ],
            pk="id",
        )
        _copy_table(
            rankings,
            "ingestion_log",
            [
                "id", "season", "data_type", "rows_ingested",
                "started_at", "completed_at", "status", "error_message",
            ],
            pk="id",
        )
        rankings.close()

    # Resync Postgres autoincrement sequences so future INSERTs don't collide
    # with copied PKs. (Safe to run even if no rows were copied.)
    with SessionLocal() as session:
        for table, col in [
            ("blog_posts", "id"),
            ("player_season_stats", "id"),
            ("ingestion_log", "id"),
        ]:
            session.execute(
                text(
                    f"SELECT setval(pg_get_serial_sequence('{table}', '{col}'), "
                    f"COALESCE((SELECT MAX({col}) FROM {table}), 1))"
                )
            )
        session.commit()
    print("[ok] sequences resynced")


if __name__ == "__main__":
    main()

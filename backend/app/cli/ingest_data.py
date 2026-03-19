"""
CLI command for ingesting NFL data from nflverse into SQLite.

Usage:
  python -m app.cli.ingest_data refresh              # Current season
  python -m app.cli.ingest_data refresh --season 2024 # Specific season
  python -m app.cli.ingest_data status                # Show ingestion status
"""

import argparse
import sys

from app.core.config import settings
from app.db.database import RankingsSessionLocal, init_rankings_db
from app.db.stats_models import IngestionLog, Player, PlayerSeasonStats


def cmd_refresh(args):
    """Run full data refresh."""
    from app.services.nflverse_ingest import refresh_all
    season = args.season or settings.current_season
    refresh_all(season)


def cmd_status(args):
    """Show ingestion status."""
    init_rankings_db()
    session = RankingsSessionLocal()
    try:
        # Player count
        player_count = session.query(Player).count()
        print(f"\nPlayers in database: {player_count}")

        # Stats count by season
        from sqlalchemy import func
        season_counts = (
            session.query(
                PlayerSeasonStats.season,
                func.count(PlayerSeasonStats.id),
            )
            .group_by(PlayerSeasonStats.season)
            .order_by(PlayerSeasonStats.season.desc())
            .all()
        )
        if season_counts:
            print("\nPlayer-season stats:")
            for season, count in season_counts:
                print(f"  {season}: {count} rows")
        else:
            print("\nNo stats data yet. Run: python -m app.cli.ingest_data refresh")

        # Recent ingestion logs
        logs = (
            session.query(IngestionLog)
            .order_by(IngestionLog.completed_at.desc())
            .limit(10)
            .all()
        )
        if logs:
            print("\nRecent ingestion runs:")
            for log in logs:
                ts = log.completed_at.strftime("%Y-%m-%d %H:%M") if log.completed_at else "?"
                print(f"  [{ts}] {log.data_type} season={log.season} "
                      f"rows={log.rows_ingested} status={log.status}")
                if log.error_message:
                    print(f"    Error: {log.error_message[:100]}")
        print()
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="SSAT Rankings Data Ingestion")
    subparsers = parser.add_subparsers(dest="command")

    # refresh command
    refresh_parser = subparsers.add_parser("refresh", help="Refresh data from nflverse")
    refresh_parser.add_argument("--season", type=int, help="Season year (default: current)")
    refresh_parser.set_defaults(func=cmd_refresh)

    # status command
    status_parser = subparsers.add_parser("status", help="Show ingestion status")
    status_parser.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()

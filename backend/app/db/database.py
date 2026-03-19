from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path

from app.core.config import settings

Base = declarative_base()
RankingsBase = declarative_base()


def _make_engine(url: str):
    """Create engine with appropriate args for SQLite vs PostgreSQL."""
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(url, connect_args=connect_args)


# Detect if using PostgreSQL (single DB) or SQLite (two files)
if settings.database_url.startswith("postgresql"):
    # Production: single PostgreSQL database for everything
    engine = _make_engine(settings.database_url)
    rankings_engine = engine
else:
    # Local dev: two separate SQLite files
    DB_DIR = Path(__file__).parent.parent.parent / "data"
    DB_DIR.mkdir(exist_ok=True)
    engine = _make_engine(f"sqlite:///{DB_DIR}/blog.db")
    rankings_engine = _make_engine(f"sqlite:///{DB_DIR}/rankings.db")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
RankingsSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=rankings_engine)


def get_db():
    """Dependency for getting blog database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_rankings_db():
    """Dependency for getting rankings database sessions."""
    db = RankingsSessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize blog database tables."""
    from app.db.models import BlogPost  # noqa: F401
    Base.metadata.create_all(bind=engine)


def init_rankings_db():
    """Initialize rankings database tables."""
    from app.db.stats_models import Player, PlayerSeasonStats, IngestionLog  # noqa: F401
    RankingsBase.metadata.create_all(bind=rankings_engine)

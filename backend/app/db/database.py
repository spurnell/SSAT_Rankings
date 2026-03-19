from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path

# Database file location
DB_DIR = Path(__file__).parent.parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)

# --- Blog database (existing) ---
DATABASE_URL = f"sqlite:///{DB_DIR}/blog.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Rankings database (player stats) ---
RANKINGS_DB_URL = f"sqlite:///{DB_DIR}/rankings.db"
rankings_engine = create_engine(RANKINGS_DB_URL, connect_args={"check_same_thread": False})
RankingsSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=rankings_engine)
RankingsBase = declarative_base()


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

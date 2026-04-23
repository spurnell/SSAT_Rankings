from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# Single engine / session / Base for all models. Schema is managed by Alembic.
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Back-compat aliases — callers migrated piecewise; kept so existing imports
# from app.db.database continue to work after the single-engine collapse.
rankings_engine = engine
RankingsSessionLocal = SessionLocal
RankingsBase = Base


def get_db():
    """Dependency for getting a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Back-compat: older routes still depend on get_rankings_db.
get_rankings_db = get_db

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import rankings, blog
from app.models.schemas import HealthResponse
from app.db.database import init_db, init_rankings_db

app = FastAPI(
    title=settings.app_name,
    description="NFL Defensive Player Rankings using Z-Score Methodology",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rankings.router, prefix="/api", tags=["rankings"])
app.include_router(blog.router, prefix="/api", tags=["blog"])

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    init_rankings_db()

    # Auto-ingest data if rankings database is empty (e.g., first deploy to new PG)
    from app.db.database import RankingsSessionLocal
    from app.db.stats_models import PlayerSeasonStats
    session = RankingsSessionLocal()
    try:
        count = session.query(PlayerSeasonStats).count()
        if count == 0:
            import logging
            logger = logging.getLogger("uvicorn")
            logger.info("Empty rankings database detected — running data ingestion...")
            from app.services.nflverse_ingest import refresh_all
            refresh_all(settings.current_season)
            logger.info("Data ingestion complete.")
    except Exception as e:
        import logging
        logging.getLogger("uvicorn").error(f"Auto-ingestion failed: {e}")
    finally:
        session.close()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {
        "message": "Welcome to SSAT Rankings API",
        "docs": "/docs",
        "health": "/health",
    }

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import rankings, blog
from app.models.schemas import HealthResponse
from app.db.database import init_db

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

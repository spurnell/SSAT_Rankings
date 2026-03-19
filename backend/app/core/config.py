import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "SSAT Rankings API"
    debug: bool = False  # Set to True only for local development
    database_url: str = "sqlite:///./data/rankings.db"
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://sportssatrankings.com",
        "https://www.sportssatrankings.com",
    ]
    anthropic_api_key: Optional[str] = None
    current_season: int = 2024

    class Config:
        env_file = ".env"


settings = Settings()

import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "SSAT Rankings API"
    debug: bool = False  # Set to True only for local development
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ssat"
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://sportssatrankings.com",
        "https://www.sportssatrankings.com",
    ]
    anthropic_api_key: Optional[str] = None
    current_season: int = 2025

    # Email (Resend)
    resend_api_key: Optional[str] = None
    resend_from_email: str = "SSAT <noreply@sportssatrankings.com>"
    app_url: str = "http://localhost:3000"

    # Auth
    session_cookie_name: str = "ssat_session"

    class Config:
        env_file = ".env"


settings = Settings()

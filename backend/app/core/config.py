from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "SSAT Rankings API"
    debug: bool = True
    database_url: str = "sqlite:///./data/rankings.db"
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    class Config:
        env_file = ".env"


settings = Settings()

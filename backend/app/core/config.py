from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    newsapi_key: str
    alpha_vantage_key: str = "your_alpha_vantage_key_here"

    postgres_user: str = "stockuser"
    postgres_password: str = "stockpass"
    postgres_db: str = "stocksentiment"
    postgres_host: str = "db"
    postgres_port: int = 5432

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    environment: str = "production"
    log_level: str = "INFO"
    refresh_interval_minutes: int = 15

    tracked_stocks: List[str] = [
        "AAPL", "GOOGL", "META", "AMZN", "NFLX",
        "TSLA", "MSFT", "NVDA", "AMD", "ORCL"
    ]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

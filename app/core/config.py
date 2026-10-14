from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "RBI India Economic Dashboard API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Database settings: SQLite for early local prototype, PostgreSQL in production
    DATABASE_URL: str = "sqlite:///./rbi_data.db"

    # Data Storage Directories
    RAW_DATA_DIR: str = "./data/raw"
    PROCESSED_DATA_DIR: str = "./data/processed"
    EXPORTS_DATA_DIR: str = "./data/exports"

    # Logging
    LOG_LEVEL: str = "INFO"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def sync_database_url(self) -> str:
        # Standardize postgres:// to postgresql:// or postgresql+psycopg://
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://") and "+psycopg" not in url and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    def ensure_directories(self) -> None:
        """Create storage directories if they do not exist."""
        Path(self.RAW_DATA_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.PROCESSED_DATA_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.EXPORTS_DATA_DIR).mkdir(parents=True, exist_ok=True)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

"""
Settings Configuration
Environment variables and application settings
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # Database
    DB_NAME: str = "stock_investment_db"
    DB_USER: str = "wonny"
    DB_PASSWORD: str = ""
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432

    # DART API
    DART_API_KEY: str

    # Korea Investment Securities
    KIS_APP_KEY: Optional[str] = None
    KIS_APP_SECRET: Optional[str] = None
    KIS_ACCOUNT_NO: Optional[str] = None
    KIS_CANO: Optional[str] = None
    KIS_ACNT_PRDT_CD: Optional[str] = None

    # Gemini API (backup)
    GEMINI_API_KEY: Optional[str] = None

    # Anthropic Claude API
    ANTHROPIC_API_KEY: Optional[str] = None

    # Monitoring
    SLACK_WEBHOOK_URL: Optional[str] = None

    # Application
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

"""
Centralised application settings.
Loaded from environment variables / .env file at startup.
"""

from dataclasses import dataclass, field


@dataclass
class Settings:
    """Application-wide configuration."""

    APP_NAME: str = "AWARE-AI"
    DEBUG: bool = False
    DATABASE_URL: str = ""
    WEATHER_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LOG_LEVEL: str = "INFO"

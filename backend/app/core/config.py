from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # -----------------------------------------------------------------------
    # App
    # -----------------------------------------------------------------------
    APP_NAME: str = "MeraCodeLikhDo"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://meracodelikhdo.in",
    ]

    # -----------------------------------------------------------------------
    # Database
    # -----------------------------------------------------------------------
    DATABASE_URL: str = "postgresql://mcld:mcld2026@localhost:5432/mcld_db"

    # -----------------------------------------------------------------------
    # Google Earth Engine
    # -----------------------------------------------------------------------
    GEE_SERVICE_ACCOUNT: str = ""
    GEE_KEY_FILE: str = "gee_key.json"
    USE_DEMO_DATA: bool = True  # Use pre-computed demo data when GEE not configured

    # -----------------------------------------------------------------------
    # LLM / NLG
    # -----------------------------------------------------------------------
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    DEFAULT_LLM_PROVIDER: str = "gemini"  # "openai" | "gemini" | "mock"

    # -----------------------------------------------------------------------
    # Twilio (SMS / WhatsApp)
    # -----------------------------------------------------------------------
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = "+14155238886"

    # -----------------------------------------------------------------------
    # Redis cache
    # -----------------------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379"

    # -----------------------------------------------------------------------
    # Pilot AOI defaults
    # -----------------------------------------------------------------------
    DEFAULT_AOI_NAME: str = "Bhakra_Canal_Command_Punjab"
    DEFAULT_SEASON: str = "kharif_2025"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()

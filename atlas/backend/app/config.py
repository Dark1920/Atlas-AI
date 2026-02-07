"""
Atlas Configuration Settings
"""
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "Atlas Risk API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # API
    api_v1_prefix: str = "/api/v1"
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/atlas"
    database_echo: bool = False
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 300  # 5 minutes
    
    # ML Model
    model_path: str = "models/risk_model.joblib"
    explainer_path: str = "models/shap_explainer.joblib"
    
    # Risk Thresholds
    risk_critical_threshold: int = 80
    risk_high_threshold: int = 60
    risk_medium_threshold: int = 40
    
    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        protected_namespaces = ()


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

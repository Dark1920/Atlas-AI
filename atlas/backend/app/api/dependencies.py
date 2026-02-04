"""
API Dependencies - Dependency injection for FastAPI routes
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import async_session_maker
from app.services.risk_scorer import RiskScorer
from app.services.explainer import ExplainabilityEngine
from app.services.feature_engine import FeatureEngineer
from app.services.audit_logger import AuditLogger
from app.services.redis_cache import get_cache, RedisCache
from app.services.alert_service import get_alert_service, AlertService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


# Singleton instances for services
_risk_scorer: RiskScorer | None = None
_explainer: ExplainabilityEngine | None = None
_feature_engineer: FeatureEngineer | None = None
_audit_logger: AuditLogger | None = None


def get_risk_scorer() -> RiskScorer:
    """Get or create RiskScorer singleton."""
    global _risk_scorer
    if _risk_scorer is None:
        _risk_scorer = RiskScorer()
    return _risk_scorer


def get_explainer() -> ExplainabilityEngine:
    """Get or create ExplainabilityEngine singleton."""
    global _explainer
    if _explainer is None:
        _explainer = ExplainabilityEngine()
    return _explainer


def get_feature_engineer() -> FeatureEngineer:
    """Get or create FeatureEngineer singleton."""
    global _feature_engineer
    if _feature_engineer is None:
        _feature_engineer = FeatureEngineer()
    return _feature_engineer


def get_audit_logger() -> AuditLogger:
    """Get or create AuditLogger singleton."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def get_redis_cache() -> RedisCache:
    """Get Redis cache instance."""
    return get_cache()


def get_alert_service_dep() -> AlertService:
    """Get alert service instance."""
    return get_alert_service()

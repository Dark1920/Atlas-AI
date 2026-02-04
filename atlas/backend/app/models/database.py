"""
SQLAlchemy Database Models and Connection
"""
from datetime import datetime
from typing import Optional
import json

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Text, Boolean,
    ForeignKey, JSON, create_engine, Index
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class TransactionRecord(Base):
    """Stored transaction records."""
    __tablename__ = "transactions"
    
    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    merchant_id = Column(String(50), nullable=False, index=True)
    merchant_category = Column(String(100))
    
    # Location
    location_country = Column(String(3))
    location_city = Column(String(100))
    location_lat = Column(Float)
    location_lon = Column(Float)
    
    # Device
    device_fingerprint = Column(String(100))
    device_type = Column(String(50))
    device_browser = Column(String(50))
    device_os = Column(String(50))
    
    # Timestamps
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Computed features (stored for audit)
    features = Column(JSON)
    
    # Relationship to risk assessment
    risk_assessment = relationship("RiskAssessmentRecord", back_populates="transaction", uselist=False)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_merchant_timestamp', 'merchant_id', 'timestamp'),
    )


class RiskAssessmentRecord(Base):
    """Risk assessment results with explainability data."""
    __tablename__ = "risk_assessments"
    
    id = Column(String(50), primary_key=True)
    transaction_id = Column(String(50), ForeignKey("transactions.id"), nullable=False, unique=True)
    
    # Risk scoring
    risk_score = Column(Integer, nullable=False)
    risk_level = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=False)
    recommended_action = Column(String(20), nullable=False)
    
    # Actual decision (may differ from recommendation)
    actual_action = Column(String(20))
    action_taken_by = Column(String(50))
    action_taken_at = Column(DateTime)
    
    # Model info
    model_version = Column(String(50))
    processing_time_ms = Column(Float)
    
    # SHAP values and explanations (stored as JSON)
    shap_values = Column(JSON)
    feature_values = Column(JSON)
    top_factors = Column(JSON)
    explanation_technical = Column(JSON)
    explanation_business = Column(JSON)
    explanation_user = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    transaction = relationship("TransactionRecord", back_populates="risk_assessment")
    
    # Index for risk queries
    __table_args__ = (
        Index('idx_risk_level', 'risk_level'),
        Index('idx_risk_score', 'risk_score'),
        Index('idx_created_at', 'created_at'),
    )


class AuditLogRecord(Base):
    """Immutable audit trail for all decisions."""
    __tablename__ = "audit_logs"
    
    id = Column(String(50), primary_key=True)
    transaction_id = Column(String(50), nullable=False, index=True)
    
    # Action details
    action = Column(String(50), nullable=False)
    previous_state = Column(JSON)
    new_state = Column(JSON)
    
    # Context
    risk_score = Column(Integer)
    model_version = Column(String(50))
    
    # Actor
    actor_type = Column(String(20))  # 'system', 'operator', 'user'
    actor_id = Column(String(50))
    
    # Metadata
    reason = Column(Text)
    ip_address = Column(String(50))
    
    # Timestamp (immutable)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Hash for tamper detection
    record_hash = Column(String(64))
    
    __table_args__ = (
        Index('idx_audit_timestamp', 'timestamp'),
        Index('idx_audit_actor', 'actor_type', 'actor_id'),
    )


class UserProfile(Base):
    """User profile with behavioral baselines."""
    __tablename__ = "user_profiles"
    
    user_id = Column(String(50), primary_key=True)
    
    # Spending patterns
    avg_transaction_amount = Column(Float, default=0)
    std_transaction_amount = Column(Float, default=0)
    avg_transactions_per_day = Column(Float, default=0)
    total_transactions = Column(Integer, default=0)
    total_amount = Column(Float, default=0)
    
    # Location patterns
    common_countries = Column(JSON, default=list)
    last_known_country = Column(String(3))
    last_known_city = Column(String(100))
    last_location_lat = Column(Float)
    last_location_lon = Column(Float)
    
    # Device patterns
    known_devices = Column(JSON, default=list)
    last_device_fingerprint = Column(String(100))
    
    # Time patterns
    typical_hours = Column(JSON, default=list)
    last_transaction_at = Column(DateTime)
    
    # Risk history
    fraud_count = Column(Integer, default=0)
    review_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlertRecord(Base):
    """Security alert records."""
    __tablename__ = "alerts"
    
    id = Column(String(50), primary_key=True)
    transaction_id = Column(String(50), nullable=False, index=True)
    
    # Alert details
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    status = Column(String(20), default="active")
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # Risk context
    risk_score = Column(Integer, nullable=False)
    risk_level = Column(String(20), nullable=False)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    # Acknowledgment/Resolution
    acknowledged_at = Column(DateTime)
    acknowledged_by = Column(String(50))
    resolved_at = Column(DateTime)
    resolved_by = Column(String(50))
    resolution = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    __table_args__ = (
        Index('idx_alert_status', 'status'),
        Index('idx_alert_severity', 'severity'),
        Index('idx_alert_created', 'created_at'),
    )


# Async engine and session
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_size=20,
    max_overflow=10,
)

async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initialize database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")


async def get_async_session() -> AsyncSession:
    """Get async database session."""
    async with async_session_maker() as session:
        yield session

"""
Pydantic Schemas for API request/response validation
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Risk level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendedAction(str, Enum):
    """Recommended action for a transaction."""
    APPROVE = "approve"
    REVIEW = "review"
    BLOCK = "block"


class ExplanationTier(str, Enum):
    """Explanation detail level."""
    TECHNICAL = "technical"
    BUSINESS = "business"
    USER = "user"


# Location Schema
class Location(BaseModel):
    """Geographic location data."""
    country: str = Field(..., example="US")
    city: Optional[str] = Field(None, example="New York")
    latitude: Optional[float] = Field(None, example=40.7128)
    longitude: Optional[float] = Field(None, example=-74.0060)


# Device Schema
class Device(BaseModel):
    """Device information."""
    fingerprint: str = Field(..., example="fp_abc123xyz")
    type: str = Field("desktop", example="mobile")
    browser: Optional[str] = Field(None, example="Chrome")
    os: Optional[str] = Field(None, example="iOS")


# Transaction Schemas
class TransactionBase(BaseModel):
    """Base transaction data."""
    amount: float = Field(..., gt=0, example=150.00)
    currency: str = Field("USD", example="USD")
    merchant_id: str = Field(..., example="merch_12345")
    merchant_category: str = Field(..., example="electronics")
    location: Location
    device: Device


class TransactionCreate(TransactionBase):
    """Transaction creation request."""
    user_id: str = Field(..., example="user_abc123")
    timestamp: Optional[datetime] = Field(None)


class Transaction(TransactionBase):
    """Full transaction with ID and timestamps."""
    transaction_id: str = Field(..., example="txn_xyz789")
    user_id: str = Field(..., example="user_abc123")
    timestamp: datetime
    
    class Config:
        from_attributes = True


# Feature Contribution for SHAP
class FeatureContribution(BaseModel):
    """Single feature's contribution to risk score."""
    feature_name: str = Field(..., example="amount_zscore")
    display_name: str = Field(..., example="Amount Deviation")
    value: Any = Field(..., example=3.5)
    impact: float = Field(..., example=15.2)
    impact_percentage: float = Field(..., example=28.5)
    direction: str = Field(..., example="increases_risk")


# Explanation Schemas
class TechnicalExplanation(BaseModel):
    """Technical explanation for compliance teams."""
    model_version: str
    base_risk: float
    shap_values: Dict[str, float]
    feature_values: Dict[str, Any]
    confidence_interval: tuple[float, float]
    
    class Config:
        protected_namespaces = ()


class RiskFactor(BaseModel):
    """Single risk factor for business explanation."""
    title: str
    description: str
    impact: float
    icon: str


class BusinessExplanation(BaseModel):
    """Business explanation for analysts."""
    summary: str
    top_factors: List[RiskFactor]
    comparison_to_baseline: str


class UserExplanation(BaseModel):
    """User-friendly explanation for cardholders."""
    headline: str
    reasons: List[str]
    what_this_means: str
    next_steps: str


class FullExplanation(BaseModel):
    """Complete explanation with all three tiers."""
    technical: TechnicalExplanation
    business: BusinessExplanation
    user: UserExplanation


# Risk Assessment Response
class RiskAssessment(BaseModel):
    """Complete risk assessment response."""
    transaction_id: str = Field(..., example="txn_xyz789")
    risk_score: int = Field(..., ge=0, le=100, example=87)
    risk_level: RiskLevel = Field(..., example=RiskLevel.HIGH)
    confidence: float = Field(..., ge=0, le=1, example=0.92)
    recommended_action: RecommendedAction = Field(..., example=RecommendedAction.REVIEW)
    processing_time_ms: float = Field(..., example=45.23)
    
    # Top contributing factors (for quick display)
    top_factors: List[FeatureContribution] = Field(default_factory=list)
    
    # Full explanation (optional, included on detail requests)
    explanation: Optional[FullExplanation] = None
    
    class Config:
        from_attributes = True


# Transaction List Response
class TransactionListItem(BaseModel):
    """Transaction item for list display."""
    transaction_id: str
    user_id: str
    amount: float
    currency: str
    merchant_id: str
    merchant_category: str
    location_country: str
    timestamp: datetime
    risk_score: int
    risk_level: RiskLevel
    recommended_action: RecommendedAction


class TransactionListResponse(BaseModel):
    """Paginated transaction list response."""
    transactions: List[TransactionListItem]
    total: int
    page: int
    page_size: int
    has_more: bool


# Dashboard Statistics
class DashboardStats(BaseModel):
    """Dashboard summary statistics."""
    total_transactions_today: int
    total_amount_today: float
    fraud_detected_today: int
    fraud_amount_blocked: float
    average_risk_score: float
    false_positive_rate: float
    transactions_by_risk_level: Dict[str, int]


# Audit Log
class AuditLogEntry(BaseModel):
    """Audit log entry for compliance."""
    id: str
    transaction_id: str
    timestamp: datetime
    action: str
    risk_score: int
    model_version: str
    operator_id: Optional[str] = None
    notes: Optional[str] = None
    
    class Config:
        protected_namespaces = ()


# Alert Schemas
class AlertSeverity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AlertStatus(str, Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class AlertType(str, Enum):
    """Alert types."""
    HIGH_RISK_TRANSACTION = "high_risk_transaction"
    FRAUD_PATTERN = "fraud_pattern"
    VELOCITY_ANOMALY = "velocity_anomaly"
    LOCATION_ANOMALY = "location_anomaly"
    DEVICE_ANOMALY = "device_anomaly"
    AMOUNT_ANOMALY = "amount_anomaly"
    MULTIPLE_FLAGS = "multiple_flags"


class Alert(BaseModel):
    """Security alert."""
    id: str
    transaction_id: str
    alert_type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    title: str
    description: str
    risk_score: int
    risk_level: RiskLevel
    alert_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None


class AlertListResponse(BaseModel):
    """Alert list response."""
    alerts: List[Alert]
    total: int
    page: int
    page_size: int
    has_more: bool


class AlertStats(BaseModel):
    """Alert statistics."""
    active_alerts: int
    total_alerts: int
    by_severity: Dict[str, int]
    by_type: Dict[str, int]


# Pattern Detection Schemas
class FraudPattern(BaseModel):
    """Detected fraud pattern."""
    id: str
    pattern_type: str
    description: str
    confidence: float
    affected_transactions: List[str]
    affected_users: List[str]
    pattern_metadata: Dict[str, Any] = Field(default_factory=dict)
    detected_at: datetime


class PatternListResponse(BaseModel):
    """Pattern list response."""
    patterns: List[FraudPattern]
    total: int

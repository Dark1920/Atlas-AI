"""
Alert Service
Real-time security alert system inspired by Deriv's SecAI bot
Generates and manages alerts for high-risk transactions
"""
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
import logging

from app.models.schemas import RiskAssessment, RiskLevel
from app.services.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


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


class Alert:
    """Alert data structure."""
    
    def __init__(
        self,
        alert_id: str,
        transaction_id: str,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        description: str,
        risk_score: int,
        risk_level: RiskLevel,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = alert_id
        self.transaction_id = transaction_id
        self.alert_type = alert_type
        self.severity = severity
        self.title = title
        self.description = description
        self.risk_score = risk_score
        self.risk_level = risk_level
        self.metadata = metadata or {}
        self.status = AlertStatus.ACTIVE
        self.created_at = created_at or datetime.utcnow()
        self.acknowledged_at: Optional[datetime] = None
        self.acknowledged_by: Optional[str] = None
        self.resolved_at: Optional[datetime] = None


class AlertService:
    """
    Alert service for generating and managing security alerts.
    Inspired by Deriv's SecAI bot for real-time threat detection.
    """
    
    def __init__(self):
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self.audit_logger = AuditLogger()
    
    def generate_alert(
        self,
        transaction_id: str,
        risk_assessment: RiskAssessment,
        transaction: Dict[str, Any],
        alert_type: Optional[AlertType] = None
    ) -> Optional[Alert]:
        """
        Generate alert for high-risk transaction.
        
        Args:
            transaction_id: Transaction ID
            risk_assessment: Risk assessment result
            transaction: Transaction data
            alert_type: Specific alert type (auto-detected if None)
        
        Returns:
            Alert object if generated, None otherwise
        """
        # Only generate alerts for high/critical risk
        if risk_assessment.risk_level not in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            return None
        
        # Determine alert type if not specified
        if alert_type is None:
            alert_type = self._detect_alert_type(risk_assessment, transaction)
        
        # Determine severity based on risk level
        if risk_assessment.risk_level == RiskLevel.CRITICAL:
            severity = AlertSeverity.CRITICAL
        elif risk_assessment.risk_score >= 75:
            severity = AlertSeverity.HIGH
        else:
            severity = AlertSeverity.MEDIUM
        
        # Generate alert ID
        alert_id = f"alert_{uuid.uuid4().hex[:12]}"
        
        # Build alert metadata
        metadata = {
            "risk_score": risk_assessment.risk_score,
            "confidence": risk_assessment.confidence,
            "recommended_action": risk_assessment.recommended_action.value,
            "top_factors": [
                {
                    "feature": f.feature_name,
                    "impact": f.impact,
                    "display_name": f.display_name
                }
                for f in risk_assessment.top_factors[:3]
            ],
            "user_id": transaction.get("user_id"),
            "amount": transaction.get("amount"),
            "merchant_category": transaction.get("merchant_category"),
            "location": transaction.get("location", {}).get("country"),
        }
        
        # Generate title and description
        title, description = self._generate_alert_content(
            alert_type, risk_assessment, transaction, metadata
        )
        
        # Create alert
        alert = Alert(
            alert_id=alert_id,
            transaction_id=transaction_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            description=description,
            risk_score=risk_assessment.risk_score,
            risk_level=risk_assessment.risk_level,
            metadata=metadata
        )
        
        # Store alert
        self._active_alerts[alert_id] = alert
        self._alert_history.append(alert)
        
        # Keep only last 1000 alerts in history
        if len(self._alert_history) > 1000:
            self._alert_history = self._alert_history[-1000:]
        
        logger.info(
            f"Alert generated: {alert_id} for transaction {transaction_id} "
            f"({severity.value}, {alert_type.value})"
        )
        
        return alert
    
    def _detect_alert_type(
        self,
        risk_assessment: RiskAssessment,
        transaction: Dict[str, Any]
    ) -> AlertType:
        """Detect alert type based on risk factors."""
        top_factors = risk_assessment.top_factors
        
        if not top_factors:
            return AlertType.HIGH_RISK_TRANSACTION
        
        # Check for multiple high-impact factors
        high_impact_count = sum(1 for f in top_factors if abs(f.impact) > 10)
        if high_impact_count >= 3:
            return AlertType.MULTIPLE_FLAGS
        
        # Check top factor
        top_factor = top_factors[0]
        factor_name = top_factor.feature_name
        
        if "velocity" in factor_name or "txn_count" in factor_name:
            return AlertType.VELOCITY_ANOMALY
        elif "location" in factor_name or "distance" in factor_name or "country" in factor_name:
            return AlertType.LOCATION_ANOMALY
        elif "device" in factor_name:
            return AlertType.DEVICE_ANOMALY
        elif "amount" in factor_name:
            return AlertType.AMOUNT_ANOMALY
        else:
            return AlertType.HIGH_RISK_TRANSACTION
    
    def _generate_alert_content(
        self,
        alert_type: AlertType,
        risk_assessment: RiskAssessment,
        transaction: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> tuple[str, str]:
        """Generate alert title and description."""
        amount = transaction.get("amount", 0)
        user_id = transaction.get("user_id", "unknown")
        merchant = transaction.get("merchant_category", "unknown")
        location = transaction.get("location", {}).get("country", "unknown")
        
        # Base title
        if risk_assessment.risk_level == RiskLevel.CRITICAL:
            title = f"🚨 CRITICAL: High-Risk Transaction Detected"
        else:
            title = f"⚠️ High-Risk Transaction Alert"
        
        # Type-specific titles
        type_titles = {
            AlertType.VELOCITY_ANOMALY: "🚨 Velocity Anomaly Detected",
            AlertType.LOCATION_ANOMALY: "🌍 Location Anomaly Detected",
            AlertType.DEVICE_ANOMALY: "📱 Device Anomaly Detected",
            AlertType.AMOUNT_ANOMALY: "💰 Amount Anomaly Detected",
            AlertType.MULTIPLE_FLAGS: "🚨 Multiple Risk Flags Detected",
            AlertType.FRAUD_PATTERN: "🔍 Fraud Pattern Detected",
        }
        title = type_titles.get(alert_type, title)
        
        # Build description
        description_parts = [
            f"Transaction {risk_assessment.transaction_id} scored {risk_assessment.risk_score}/100 "
            f"({risk_assessment.risk_level.value.upper()} risk)."
        ]
        
        if top_factors := metadata.get("top_factors", []):
            top_factor = top_factors[0]
            description_parts.append(
                f"Primary concern: {top_factor['display_name']} "
                f"(impact: {top_factor['impact']:.1f} points)."
            )
        
        description_parts.append(
            f"Amount: ${amount:.2f} | User: {user_id} | "
            f"Merchant: {merchant} | Location: {location}"
        )
        
        description_parts.append(
            f"Recommended action: {risk_assessment.recommended_action.value.upper()}"
        )
        
        description = " ".join(description_parts)
        
        return title, description
    
    def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[AlertType] = None,
        limit: int = 100
    ) -> List[Alert]:
        """
        Get active alerts with optional filtering.
        
        Args:
            severity: Filter by severity
            alert_type: Filter by alert type
            limit: Maximum number of alerts to return
        
        Returns:
            List of active alerts
        """
        alerts = list(self._active_alerts.values())
        
        # Apply filters
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        
        # Sort by created_at (newest first)
        alerts.sort(key=lambda x: x.created_at, reverse=True)
        
        return alerts[:limit]
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID."""
        return self._active_alerts.get(alert_id)
    
    def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str,
        notes: Optional[str] = None
    ) -> Optional[Alert]:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: Alert ID
            acknowledged_by: User/operator ID who acknowledged
            notes: Optional notes
        
        Returns:
            Updated alert or None if not found
        """
        alert = self._active_alerts.get(alert_id)
        if not alert:
            return None
        
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = acknowledged_by
        
        if notes:
            alert.metadata["acknowledgment_notes"] = notes
        
        logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        
        return alert
    
    def resolve_alert(
        self,
        alert_id: str,
        resolved_by: str,
        resolution: str
    ) -> Optional[Alert]:
        """
        Resolve an alert.
        
        Args:
            alert_id: Alert ID
            resolved_by: User/operator ID who resolved
            resolution: Resolution description
        
        Returns:
            Updated alert or None if not found
        """
        alert = self._active_alerts.get(alert_id)
        if not alert:
            return None
        
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        alert.metadata["resolved_by"] = resolved_by
        alert.metadata["resolution"] = resolution
        
        # Remove from active alerts
        del self._active_alerts[alert_id]
        
        logger.info(f"Alert {alert_id} resolved by {resolved_by}")
        
        return alert
    
    def dismiss_alert(
        self,
        alert_id: str,
        dismissed_by: str,
        reason: str
    ) -> Optional[Alert]:
        """
        Dismiss an alert (false positive).
        
        Args:
            alert_id: Alert ID
            dismissed_by: User/operator ID who dismissed
            reason: Dismissal reason
        
        Returns:
            Updated alert or None if not found
        """
        alert = self._active_alerts.get(alert_id)
        if not alert:
            return None
        
        alert.status = AlertStatus.DISMISSED
        alert.metadata["dismissed_by"] = dismissed_by
        alert.metadata["dismissal_reason"] = reason
        
        # Remove from active alerts
        del self._active_alerts[alert_id]
        
        logger.info(f"Alert {alert_id} dismissed by {dismissed_by}: {reason}")
        
        return alert
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics."""
        active_count = len(self._active_alerts)
        
        by_severity = {
            AlertSeverity.CRITICAL.value: 0,
            AlertSeverity.HIGH.value: 0,
            AlertSeverity.MEDIUM.value: 0,
            AlertSeverity.LOW.value: 0,
        }
        
        by_type = {}
        
        for alert in self._active_alerts.values():
            by_severity[alert.severity.value] = by_severity.get(alert.severity.value, 0) + 1
            by_type[alert.alert_type.value] = by_type.get(alert.alert_type.value, 0) + 1
        
        return {
            "active_alerts": active_count,
            "total_alerts": len(self._alert_history),
            "by_severity": by_severity,
            "by_type": by_type,
        }


# Singleton instance
_alert_service_instance: Optional[AlertService] = None


def get_alert_service() -> AlertService:
    """Get alert service singleton instance."""
    global _alert_service_instance
    if _alert_service_instance is None:
        _alert_service_instance = AlertService()
    return _alert_service_instance

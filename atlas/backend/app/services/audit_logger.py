"""
Audit Logger Service
Creates immutable audit trail for all risk decisions
"""
import uuid
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import AuditLogRecord
from app.models.schemas import RiskAssessment

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Creates and manages immutable audit logs for compliance.
    All risk decisions are logged with tamper-detection hashing.
    """
    
    def __init__(self):
        self._pending_logs: list = []
    
    def create_decision_log(
        self,
        transaction_id: str,
        risk_assessment: RiskAssessment,
        action: str = "score",
        actor_type: str = "system",
        actor_id: Optional[str] = None,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        previous_state: Optional[Dict[str, Any]] = None
    ) -> AuditLogRecord:
        """
        Create an audit log entry for a risk decision.
        
        Args:
            transaction_id: Transaction being logged
            risk_assessment: Risk assessment result
            action: Action taken (score, approve, reject, review)
            actor_type: Type of actor (system, operator, user)
            actor_id: ID of actor if not system
            reason: Optional reason for action
            ip_address: Request IP address
            previous_state: Previous state if this is an update
        
        Returns:
            AuditLogRecord ready to be persisted
        """
        log_id = f"audit_{uuid.uuid4().hex[:16]}"
        timestamp = datetime.utcnow()
        
        # Build new state
        new_state = {
            "risk_score": risk_assessment.risk_score,
            "risk_level": risk_assessment.risk_level.value,
            "recommended_action": risk_assessment.recommended_action.value,
            "confidence": risk_assessment.confidence,
            "processing_time_ms": risk_assessment.processing_time_ms,
            "top_factors": [
                {"name": f.feature_name, "impact": f.impact}
                for f in risk_assessment.top_factors
            ] if risk_assessment.top_factors else []
        }
        
        # Create record
        record = AuditLogRecord(
            id=log_id,
            transaction_id=transaction_id,
            action=action,
            previous_state=previous_state,
            new_state=new_state,
            risk_score=risk_assessment.risk_score,
            model_version="1.0.0",  # Would come from model manager
            actor_type=actor_type,
            actor_id=actor_id,
            reason=reason,
            ip_address=ip_address,
            timestamp=timestamp,
            record_hash=None  # Will be set below
        )
        
        # Generate tamper-detection hash
        record.record_hash = self._generate_hash(record)
        
        logger.info(
            f"Audit log created: {log_id} for txn {transaction_id} "
            f"action={action} risk_score={risk_assessment.risk_score}"
        )
        
        return record
    
    def _generate_hash(self, record: AuditLogRecord) -> str:
        """
        Generate SHA-256 hash for tamper detection.
        """
        hash_content = {
            "id": record.id,
            "transaction_id": record.transaction_id,
            "action": record.action,
            "new_state": record.new_state,
            "risk_score": record.risk_score,
            "timestamp": record.timestamp.isoformat() if record.timestamp else None,
            "actor_type": record.actor_type,
            "actor_id": record.actor_id,
        }
        
        content_str = json.dumps(hash_content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def verify_integrity(self, record: AuditLogRecord) -> bool:
        """
        Verify the integrity of an audit log record.
        
        Returns:
            True if record hash matches, False if tampered
        """
        expected_hash = self._generate_hash(record)
        return record.record_hash == expected_hash
    
    async def persist_log(
        self,
        session: AsyncSession,
        record: AuditLogRecord
    ) -> AuditLogRecord:
        """
        Persist audit log to database.
        
        Args:
            session: Database session
            record: Audit log record to persist
        
        Returns:
            Persisted record
        """
        session.add(record)
        await session.commit()
        await session.refresh(record)
        
        logger.debug(f"Audit log {record.id} persisted to database")
        return record
    
    async def get_transaction_audit_trail(
        self,
        session: AsyncSession,
        transaction_id: str
    ) -> list[AuditLogRecord]:
        """
        Get complete audit trail for a transaction.
        
        Args:
            session: Database session
            transaction_id: Transaction ID to query
        
        Returns:
            List of audit log records, ordered by timestamp
        """
        result = await session.execute(
            select(AuditLogRecord)
            .where(AuditLogRecord.transaction_id == transaction_id)
            .order_by(AuditLogRecord.timestamp)
        )
        
        records = result.scalars().all()
        
        # Verify integrity of each record
        for record in records:
            if not self.verify_integrity(record):
                logger.warning(
                    f"Audit log integrity check failed for {record.id}"
                )
        
        return records
    
    def log_action_override(
        self,
        transaction_id: str,
        original_action: str,
        new_action: str,
        operator_id: str,
        reason: str,
        risk_assessment: RiskAssessment,
        ip_address: Optional[str] = None
    ) -> AuditLogRecord:
        """
        Log when an operator overrides a system decision.
        
        Args:
            transaction_id: Transaction ID
            original_action: System's original recommendation
            new_action: Operator's chosen action
            operator_id: ID of the operator
            reason: Reason for override
            risk_assessment: Current risk assessment
            ip_address: Operator's IP address
        
        Returns:
            Audit log record
        """
        previous_state = {
            "action": original_action,
            "decision_type": "system"
        }
        
        return self.create_decision_log(
            transaction_id=transaction_id,
            risk_assessment=risk_assessment,
            action=f"override_to_{new_action}",
            actor_type="operator",
            actor_id=operator_id,
            reason=reason,
            ip_address=ip_address,
            previous_state=previous_state
        )

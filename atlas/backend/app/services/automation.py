"""
Automation Service
Automated response workflows for fraud detection
Inspired by Deriv's automated security systems
"""
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
import logging

from app.models.schemas import RiskAssessment, RiskLevel, RecommendedAction

logger = logging.getLogger(__name__)


class AutomationRuleType(str, Enum):
    """Automation rule types."""
    AUTO_BLOCK = "auto_block"
    AUTO_REVIEW = "auto_review"
    AUTO_ESCALATE = "auto_escalate"
    NOTIFY = "notify"


class AutomationRule:
    """Automation rule definition."""
    
    def __init__(
        self,
        rule_id: str,
        rule_type: AutomationRuleType,
        name: str,
        description: str,
        conditions: Dict[str, Any],
        enabled: bool = True
    ):
        self.id = rule_id
        self.rule_type = rule_type
        self.name = name
        self.description = description
        self.conditions = conditions
        self.enabled = enabled
        self.created_at = datetime.utcnow()
        self.execution_count = 0
        self.last_executed_at: Optional[datetime] = None


class AutomationService:
    """
    Automation service for automated fraud response workflows.
    Inspired by Deriv's automated security systems.
    """
    
    def __init__(self):
        self._rules: Dict[str, AutomationRule] = {}
        self._execution_log: List[Dict[str, Any]] = []
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default automation rules."""
        # Auto-block critical risk transactions
        auto_block_rule = AutomationRule(
            rule_id="auto_block_critical",
            rule_type=AutomationRuleType.AUTO_BLOCK,
            name="Auto-Block Critical Risk",
            description="Automatically block transactions with critical risk (score >= 80)",
            conditions={
                "risk_level": "critical",
                "risk_score_min": 80,
            }
        )
        self._rules[auto_block_rule.id] = auto_block_rule
        
        # Auto-review high risk transactions
        auto_review_rule = AutomationRule(
            rule_id="auto_review_high",
            rule_type=AutomationRuleType.AUTO_REVIEW,
            name="Auto-Review High Risk",
            description="Automatically flag high-risk transactions (score >= 60) for review",
            conditions={
                "risk_level": "high",
                "risk_score_min": 60,
            }
        )
        self._rules[auto_review_rule.id] = auto_review_rule
        
        # Auto-escalate multiple flags
        auto_escalate_rule = AutomationRule(
            rule_id="auto_escalate_multiple_flags",
            rule_type=AutomationRuleType.AUTO_ESCALATE,
            name="Auto-Escalate Multiple Flags",
            description="Escalate transactions with 3+ high-impact risk factors",
            conditions={
                "top_factors_count": 3,
                "min_factor_impact": 10,
            }
        )
        self._rules[auto_escalate_rule.id] = auto_escalate_rule
    
    def evaluate_rules(
        self,
        transaction_id: str,
        risk_assessment: RiskAssessment,
        transaction: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate automation rules for a transaction.
        
        Args:
            transaction_id: Transaction ID
            risk_assessment: Risk assessment result
            transaction: Transaction data
        
        Returns:
            List of rule execution results
        """
        executed_rules = []
        
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            
            if self._evaluate_rule(rule, risk_assessment, transaction):
                result = self._execute_rule(rule, transaction_id, risk_assessment, transaction)
                executed_rules.append(result)
        
        return executed_rules
    
    def _evaluate_rule(
        self,
        rule: AutomationRule,
        risk_assessment: RiskAssessment,
        transaction: Dict[str, Any]
    ) -> bool:
        """Evaluate if a rule's conditions are met."""
        conditions = rule.conditions
        
        # Check risk level
        if "risk_level" in conditions:
            if risk_assessment.risk_level.value != conditions["risk_level"]:
                return False
        
        # Check risk score
        if "risk_score_min" in conditions:
            if risk_assessment.risk_score < conditions["risk_score_min"]:
                return False
        
        # Check top factors count
        if "top_factors_count" in conditions:
            required_count = conditions["top_factors_count"]
            min_impact = conditions.get("min_factor_impact", 0)
            
            high_impact_factors = [
                f for f in risk_assessment.top_factors
                if abs(f.impact) >= min_impact
            ]
            
            if len(high_impact_factors) < required_count:
                return False
        
        return True
    
    def _execute_rule(
        self,
        rule: AutomationRule,
        transaction_id: str,
        risk_assessment: RiskAssessment,
        transaction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an automation rule."""
        rule.execution_count += 1
        rule.last_executed_at = datetime.utcnow()
        
        result = {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "rule_type": rule.rule_type.value,
            "transaction_id": transaction_id,
            "executed_at": datetime.utcnow().isoformat(),
            "action_taken": None,
            "success": True,
        }
        
        try:
            if rule.rule_type == AutomationRuleType.AUTO_BLOCK:
                result["action_taken"] = "blocked"
                result["message"] = f"Transaction automatically blocked by rule: {rule.name}"
                logger.info(f"Auto-blocked transaction {transaction_id} via rule {rule.id}")
            
            elif rule.rule_type == AutomationRuleType.AUTO_REVIEW:
                result["action_taken"] = "flagged_for_review"
                result["message"] = f"Transaction flagged for review by rule: {rule.name}"
                logger.info(f"Auto-flagged transaction {transaction_id} for review via rule {rule.id}")
            
            elif rule.rule_type == AutomationRuleType.AUTO_ESCALATE:
                result["action_taken"] = "escalated"
                result["message"] = f"Transaction escalated by rule: {rule.name}"
                logger.info(f"Auto-escalated transaction {transaction_id} via rule {rule.id}")
            
            elif rule.rule_type == AutomationRuleType.NOTIFY:
                result["action_taken"] = "notified"
                result["message"] = f"Notification sent by rule: {rule.name}"
                logger.info(f"Notification sent for transaction {transaction_id} via rule {rule.id}")
        
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            logger.error(f"Error executing rule {rule.id}: {e}")
        
        # Log execution
        self._execution_log.append(result)
        
        # Keep only last 1000 executions
        if len(self._execution_log) > 1000:
            self._execution_log = self._execution_log[-1000:]
        
        return result
    
    def create_rule(
        self,
        rule_type: AutomationRuleType,
        name: str,
        description: str,
        conditions: Dict[str, Any],
        enabled: bool = True
    ) -> AutomationRule:
        """Create a new automation rule."""
        rule_id = f"rule_{uuid.uuid4().hex[:12]}"
        
        rule = AutomationRule(
            rule_id=rule_id,
            rule_type=rule_type,
            name=name,
            description=description,
            conditions=conditions,
            enabled=enabled
        )
        
        self._rules[rule_id] = rule
        logger.info(f"Created automation rule: {rule_id} ({name})")
        
        return rule
    
    def get_rule(self, rule_id: str) -> Optional[AutomationRule]:
        """Get rule by ID."""
        return self._rules.get(rule_id)
    
    def get_all_rules(self, enabled_only: bool = False) -> List[AutomationRule]:
        """Get all automation rules."""
        rules = list(self._rules.values())
        
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        
        return rules
    
    def update_rule(
        self,
        rule_id: str,
        enabled: Optional[bool] = None,
        conditions: Optional[Dict[str, Any]] = None
    ) -> Optional[AutomationRule]:
        """Update an automation rule."""
        rule = self._rules.get(rule_id)
        if not rule:
            return None
        
        if enabled is not None:
            rule.enabled = enabled
        
        if conditions is not None:
            rule.conditions = {**rule.conditions, **conditions}
        
        logger.info(f"Updated automation rule: {rule_id}")
        return rule
    
    def delete_rule(self, rule_id: str) -> bool:
        """Delete an automation rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            logger.info(f"Deleted automation rule: {rule_id}")
            return True
        return False
    
    def get_execution_log(
        self,
        rule_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get automation execution log."""
        log = self._execution_log
        
        if rule_id:
            log = [e for e in log if e.get("rule_id") == rule_id]
        
        return log[-limit:]
    
    def get_automation_stats(self) -> Dict[str, Any]:
        """Get automation statistics."""
        total_executions = len(self._execution_log)
        
        by_type = {}
        for execution in self._execution_log:
            rule_type = execution.get("rule_type", "unknown")
            by_type[rule_type] = by_type.get(rule_type, 0) + 1
        
        return {
            "total_rules": len(self._rules),
            "enabled_rules": sum(1 for r in self._rules.values() if r.enabled),
            "total_executions": total_executions,
            "by_type": by_type,
        }


# Singleton instance
_automation_service_instance: Optional[AutomationService] = None


def get_automation_service() -> AutomationService:
    """Get automation service singleton instance."""
    global _automation_service_instance
    if _automation_service_instance is None:
        _automation_service_instance = AutomationService()
    return _automation_service_instance

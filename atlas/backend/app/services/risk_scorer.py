"""
Risk Scoring Service
Core service for scoring transactions and generating risk assessments
"""
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import numpy as np
import logging

from app.config import settings
from app.ml.model import model_manager
from app.services.feature_engine import FeatureEngineer
from app.models.schemas import (
    RiskAssessment, RiskLevel, RecommendedAction, 
    FeatureContribution, FullExplanation
)

logger = logging.getLogger(__name__)


class RiskScorer:
    """
    Risk scoring service that combines ML inference with explainability.
    """
    
    def __init__(self):
        self.feature_engineer = FeatureEngineer()
        self.model = model_manager
    
    async def score_transaction(
        self,
        transaction: Dict[str, Any],
        include_explanation: bool = True
    ) -> RiskAssessment:
        """
        Score a transaction for fraud risk (with Redis caching).
        
        Args:
            transaction: Transaction data dictionary
            include_explanation: Whether to include full explanation
        
        Returns:
            RiskAssessment with score, level, and explanations
        """
        start_time = time.time()
        
        # Generate transaction ID if not present
        transaction_id = transaction.get("transaction_id")
        if not transaction_id:
            transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
            transaction["transaction_id"] = transaction_id
        
        # Extract features (now async with Redis caching)
        features_dict = await self.feature_engineer.extract_features(transaction)
        features_vector = self.feature_engineer.get_feature_vector(features_dict)
        
        # Model inference
        probabilities = self.model.predict_proba(features_vector)
        fraud_probability = float(probabilities[0][1])
        
        # Convert to 0-100 risk score
        risk_score = int(fraud_probability * 100)
        
        # Classify risk level
        risk_level = self._classify_risk_level(risk_score)
        
        # Calculate confidence (based on probability distance from 0.5)
        confidence = self._calculate_confidence(fraud_probability)
        
        # Determine recommended action
        recommended_action = self._determine_action(risk_score, risk_level)
        
        # Get SHAP values for top factors
        shap_values = self.model.get_shap_values(features_vector)
        top_factors = self._extract_top_factors(
            shap_values[0],
            features_dict,
            self.model.feature_names
        )
        
        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Build response
        assessment = RiskAssessment(
            transaction_id=transaction_id,
            risk_score=risk_score,
            risk_level=risk_level,
            confidence=confidence,
            recommended_action=recommended_action,
            processing_time_ms=processing_time_ms,
            top_factors=top_factors,
            explanation=None  # Filled separately if needed
        )
        
        # Update user profile for future scoring (now async with Redis caching)
        user_id = transaction.get("user_id")
        if user_id:
            await self.feature_engineer.update_user_profile(user_id, transaction)
        
        logger.info(
            f"Transaction {transaction_id} scored: {risk_score} ({risk_level.value}) "
            f"in {processing_time_ms:.2f}ms"
        )
        
        return assessment
    
    def _classify_risk_level(self, risk_score: int) -> RiskLevel:
        """Classify risk score into risk level."""
        if risk_score >= settings.risk_critical_threshold:
            return RiskLevel.CRITICAL
        elif risk_score >= settings.risk_high_threshold:
            return RiskLevel.HIGH
        elif risk_score >= settings.risk_medium_threshold:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _calculate_confidence(self, probability: float) -> float:
        """
        Calculate confidence based on probability.
        Higher confidence when probability is far from 0.5.
        """
        # Distance from uncertainty (0.5)
        distance = abs(probability - 0.5)
        # Scale to 0-1 range (max distance is 0.5)
        confidence = min(1.0, distance * 2 + 0.5)
        return round(confidence, 3)
    
    def _determine_action(self, risk_score: int, risk_level: RiskLevel) -> RecommendedAction:
        """Determine recommended action based on risk."""
        if risk_level == RiskLevel.CRITICAL:
            return RecommendedAction.BLOCK
        elif risk_level == RiskLevel.HIGH:
            return RecommendedAction.REVIEW
        elif risk_level == RiskLevel.MEDIUM and risk_score >= 50:
            return RecommendedAction.REVIEW
        else:
            return RecommendedAction.APPROVE
    
    def _extract_top_factors(
        self,
        shap_values: np.ndarray,
        features_dict: Dict[str, float],
        feature_names: list,
        top_n: int = 5
    ) -> list[FeatureContribution]:
        """
        Extract top contributing factors from SHAP values.
        
        Args:
            shap_values: SHAP values array
            features_dict: Original feature values
            feature_names: List of feature names
            top_n: Number of top factors to return
        
        Returns:
            List of FeatureContribution objects
        """
        # Pair features with their SHAP values
        contributions = []
        total_impact = np.abs(shap_values).sum()
        
        for i, (name, shap_value) in enumerate(zip(feature_names, shap_values)):
            if abs(shap_value) > 0.01:  # Filter noise
                feature_value = features_dict.get(name, 0)
                
                # Calculate percentage of total impact
                impact_pct = (abs(shap_value) / total_impact * 100) if total_impact > 0 else 0
                
                contributions.append(FeatureContribution(
                    feature_name=name,
                    display_name=self.feature_engineer.get_feature_display_name(name),
                    value=round(feature_value, 4) if isinstance(feature_value, float) else feature_value,
                    impact=round(float(shap_value), 4),
                    impact_percentage=round(impact_pct, 1),
                    direction="increases_risk" if shap_value > 0 else "decreases_risk"
                ))
        
        # Sort by absolute impact and take top N
        contributions.sort(key=lambda x: abs(x.impact), reverse=True)
        return contributions[:top_n]
    
    async def get_detailed_explanation(
        self,
        transaction: Dict[str, Any],
        assessment: RiskAssessment
    ) -> FullExplanation:
        """
        Generate full three-tier explanation for a transaction.
        Delegated to ExplainabilityEngine.
        """
        from app.services.explainer import ExplainabilityEngine
        explainer = ExplainabilityEngine()
        
        # Get features and SHAP values (now async)
        features_dict = await self.feature_engineer.extract_features(transaction)
        features_vector = self.feature_engineer.get_feature_vector(features_dict)
        shap_values = self.model.get_shap_values(features_vector)[0]
        
        return explainer.generate_full_explanation(
            risk_score=assessment.risk_score,
            risk_level=assessment.risk_level,
            features=features_dict,
            shap_values=shap_values,
            feature_names=self.model.feature_names,
            transaction=transaction
        )

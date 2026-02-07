"""
Explainability Engine
Generates three-tier explanations for risk assessments
"""
from typing import Dict, Any, List
import numpy as np
import logging

from app.ml.model import model_manager
from app.services.feature_engine import FeatureEngineer
from app.models.schemas import (
    RiskLevel, TechnicalExplanation, BusinessExplanation, 
    UserExplanation, FullExplanation, RiskFactor
)

logger = logging.getLogger(__name__)


class ExplainabilityEngine:
    """
    Generates human-readable explanations from SHAP values.
    Three tiers: Technical (compliance), Business (analysts), User (cardholders)
    """
    
    # Templates for narrative generation
    FEATURE_TEMPLATES = {
        "amount_zscore": {
            "high": "This transaction of ${amount:.2f} is {ratio:.1f}x higher than your typical spending of ${avg:.2f}",
            "low": "This transaction amount is within your normal spending range",
        },
        "country_risk": {
            "high": "Transaction originated from {country}, which has elevated fraud risk",
            "low": "Transaction is from a low-risk country",
        },
        "is_new_device": {
            "high": "This is the first time we've seen this device used with your account",
            "low": "Transaction is from a recognized device",
        },
        "is_impossible_travel": {
            "high": "The location is {distance:.0f}km from your last transaction, which occurred only {hours:.1f} hours ago - this appears physically impossible",
            "low": "Location is consistent with your travel patterns",
        },
        "velocity_score": {
            "high": "You've made {count} transactions in the last hour, which is unusual",
            "low": "Transaction frequency is normal",
        },
        "is_night": {
            "high": "This transaction occurred at an unusual time ({hour}:00)",
            "low": "Transaction timing is within your normal hours",
        },
        "is_high_risk_merchant": {
            "high": "This merchant category ({category}) has elevated fraud rates",
            "low": "Merchant category has low fraud rates",
        },
        "distance_from_last_km": {
            "high": "Transaction is {distance:.0f}km from your last known location",
            "low": "Transaction is near your usual locations",
        },
        "is_new_country": {
            "high": "This is the first transaction we've seen from {country}",
            "low": "Country is in your usual transaction locations",
        },
    }
    
    # Icons for business explanation
    FEATURE_ICONS = {
        "amount": "💰",
        "amount_zscore": "📊",
        "country_risk": "🌍",
        "is_new_device": "📱",
        "is_impossible_travel": "✈️",
        "velocity_score": "⚡",
        "is_night": "🌙",
        "is_high_risk_merchant": "🏪",
        "distance_from_last_km": "📍",
        "is_new_country": "🗺️",
        "txn_count_1h": "⏱️",
        "behavior_anomaly_score": "🔍",
    }
    
    def __init__(self):
        self.feature_engineer = FeatureEngineer()
    
    def generate_full_explanation(
        self,
        risk_score: int,
        risk_level: RiskLevel,
        features: Dict[str, float],
        shap_values: np.ndarray,
        feature_names: List[str],
        transaction: Dict[str, Any]
    ) -> FullExplanation:
        """
        Generate complete three-tier explanation.
        
        Args:
            risk_score: Risk score 0-100
            risk_level: Risk level classification
            features: Feature dictionary
            shap_values: SHAP values array
            feature_names: List of feature names
            transaction: Original transaction data
        
        Returns:
            FullExplanation with technical, business, and user tiers
        """
        # Build SHAP contributions dict
        shap_dict = {name: float(val) for name, val in zip(feature_names, shap_values)}
        
        # Get top contributors
        sorted_features = sorted(
            shap_dict.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:5]
        
        return FullExplanation(
            technical=self._generate_technical(
                risk_score, features, shap_dict, feature_names
            ),
            business=self._generate_business(
                risk_score, risk_level, features, sorted_features, transaction
            ),
            user=self._generate_user(
                risk_score, risk_level, features, sorted_features, transaction
            )
        )
    
    def _generate_technical(
        self,
        risk_score: int,
        features: Dict[str, float],
        shap_dict: Dict[str, float],
        feature_names: List[str]
    ) -> TechnicalExplanation:
        """Generate technical explanation for compliance teams."""
        # Calculate confidence interval (simplified)
        base_risk = model_manager.get_expected_value() * 100
        confidence_interval = (
            max(0, risk_score - 5),
            min(100, risk_score + 5)
        )
        
        # Round feature values for display
        feature_values = {
            name: round(val, 4) if isinstance(val, float) else val
            for name, val in features.items()
        }
        
        # Round SHAP values
        shap_values_rounded = {
            name: round(val, 4)
            for name, val in shap_dict.items()
        }
        
        return TechnicalExplanation(
            model_version=model_manager.get_version(),
            base_risk=round(base_risk, 2),
            shap_values=shap_values_rounded,
            feature_values=feature_values,
            confidence_interval=confidence_interval
        )
    
    def _generate_business(
        self,
        risk_score: int,
        risk_level: RiskLevel,
        features: Dict[str, float],
        top_features: List[tuple],
        transaction: Dict[str, Any]
    ) -> BusinessExplanation:
        """Generate business explanation for analysts."""
        amount = transaction.get("amount", 0)
        location = transaction.get("location", {})
        
        # Build summary
        if risk_level == RiskLevel.CRITICAL:
            summary = f"Critical risk detected (Score: {risk_score}/100). Multiple high-risk indicators present. Immediate review required."
        elif risk_level == RiskLevel.HIGH:
            summary = f"High risk transaction (Score: {risk_score}/100). Several anomalies detected that warrant investigation."
        elif risk_level == RiskLevel.MEDIUM:
            summary = f"Moderate risk (Score: {risk_score}/100). Some unusual patterns detected but within acceptable thresholds."
        else:
            summary = f"Low risk transaction (Score: {risk_score}/100). Activity consistent with user's normal behavior."
        
        # Build risk factors
        risk_factors = []
        
        for feature_name, shap_value in top_features:
            if abs(shap_value) < 0.5:  # Skip low-impact features
                continue
            
            icon = self.FEATURE_ICONS.get(feature_name, "📋")
            display_name = self.feature_engineer.get_feature_display_name(feature_name)
            
            # Generate description
            description = self._generate_factor_description(
                feature_name, features, transaction, shap_value
            )
            
            risk_factors.append(RiskFactor(
                title=f"{icon} {display_name}",
                description=description,
                impact=round(shap_value, 2),
                icon=icon
            ))
        
        # Comparison to baseline
        avg_amount = features.get("amount", 0) / max(features.get("amount_vs_avg_ratio", 1), 0.01)
        comparison = f"Typical transaction for this user: ${avg_amount:.2f}. This transaction: ${amount:.2f}."
        
        return BusinessExplanation(
            summary=summary,
            top_factors=risk_factors,
            comparison_to_baseline=comparison
        )
    
    def _generate_user(
        self,
        risk_score: int,
        risk_level: RiskLevel,
        features: Dict[str, float],
        top_features: List[tuple],
        transaction: Dict[str, Any]
    ) -> UserExplanation:
        """Generate user-friendly explanation for cardholders."""
        amount = transaction.get("amount", 0)
        merchant_category = transaction.get("merchant_category", "unknown")
        
        # Headline based on risk
        if risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            headline = "We flagged this transaction for your protection"
        elif risk_level == RiskLevel.MEDIUM:
            headline = "We noticed some unusual activity"
        else:
            headline = "Transaction approved"
        
        # Generate simple reasons
        reasons = []
        for feature_name, shap_value in top_features[:3]:
            if shap_value > 1:  # Only positive (risk-increasing) factors
                reason = self._get_simple_reason(feature_name, features, transaction)
                if reason:
                    reasons.append(reason)
        
        if not reasons:
            reasons = ["This transaction matched typical patterns for your account"]
        
        # What this means
        if risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            what_this_means = "This could mean someone is trying to use your account without permission, or you might be making an unusual but legitimate purchase."
        elif risk_level == RiskLevel.MEDIUM:
            what_this_means = "The transaction has some unusual characteristics, but it may still be legitimate."
        else:
            what_this_means = "Everything looks normal with this transaction."
        
        # Next steps
        if risk_level == RiskLevel.CRITICAL:
            next_steps = "We've temporarily held this transaction. Please confirm if this was you by responding to our verification request."
        elif risk_level == RiskLevel.HIGH:
            next_steps = "Please review this transaction. If you don't recognize it, please contact us immediately."
        elif risk_level == RiskLevel.MEDIUM:
            next_steps = "No action needed, but please review your recent transactions to ensure they're all legitimate."
        else:
            next_steps = "No action needed. Your transaction has been processed successfully."
        
        return UserExplanation(
            headline=headline,
            reasons=reasons,
            what_this_means=what_this_means,
            next_steps=next_steps
        )
    
    def _generate_factor_description(
        self,
        feature_name: str,
        features: Dict[str, float],
        transaction: Dict[str, Any],
        shap_value: float
    ) -> str:
        """Generate a detailed description for a risk factor."""
        amount = transaction.get("amount", 0)
        location = transaction.get("location", {})
        
        templates = self.FEATURE_TEMPLATES.get(feature_name, {})
        template_key = "high" if shap_value > 0 else "low"
        template = templates.get(template_key)
        
        if not template:
            direction = "increased" if shap_value > 0 else "decreased"
            return f"This factor {direction} the risk score by {abs(shap_value):.1f} points"
        
        # Fill in template based on feature
        try:
            if feature_name == "amount_zscore":
                avg = amount / max(features.get("amount_vs_avg_ratio", 1), 0.01)
                return template.format(
                    amount=amount,
                    ratio=features.get("amount_vs_avg_ratio", 1),
                    avg=avg
                )
            elif feature_name == "country_risk":
                return template.format(country=location.get("country", "unknown"))
            elif feature_name == "is_impossible_travel":
                return template.format(
                    distance=features.get("distance_from_last_km", 0),
                    hours=features.get("minutes_since_last_txn", 0) / 60
                )
            elif feature_name == "velocity_score":
                return template.format(count=int(features.get("txn_count_1h", 0)))
            elif feature_name == "is_night":
                return template.format(hour=int(features.get("hour_of_day", 0)))
            elif feature_name == "is_high_risk_merchant":
                return template.format(category=transaction.get("merchant_category", "unknown"))
            elif feature_name == "distance_from_last_km":
                return template.format(distance=features.get("distance_from_last_km", 0))
            elif feature_name == "is_new_country":
                return template.format(country=location.get("country", "unknown"))
            else:
                return template
        except Exception as e:
            logger.warning(f"Error formatting template for {feature_name}: {e}")
            return f"Feature value: {features.get(feature_name, 'N/A')}"
    
    def _get_simple_reason(
        self,
        feature_name: str,
        features: Dict[str, float],
        transaction: Dict[str, Any]
    ) -> str:
        """Get a simple, user-friendly reason for a risk factor."""
        amount = transaction.get("amount", 0)
        location = transaction.get("location", {})
        
        simple_reasons = {
            "amount_zscore": f"This purchase of ${amount:.2f} is much larger than your typical spending",
            "country_risk": f"The transaction location ({location.get('country', 'unknown')}) is unusual",
            "is_new_device": "We don't recognize the device used for this transaction",
            "is_impossible_travel": "The location is very far from where you were recently",
            "velocity_score": "You've made several transactions very quickly",
            "is_night": "This transaction was made at an unusual time",
            "is_high_risk_merchant": "The merchant type has higher fraud rates",
            "is_new_country": f"This is your first transaction from {location.get('country', 'this country')}",
            "distance_from_last_km": "This location is far from where you normally shop",
        }
        
        return simple_reasons.get(feature_name, "")

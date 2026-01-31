"""
ML Model Loading and Management
"""
import os
import json
from typing import Dict, Any, Optional, Tuple
import numpy as np
import joblib
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages ML model loading and inference."""
    
    _instance: Optional["ModelManager"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.model = None
        self.base_model = None
        self.explainer = None
        self.feature_names = []
        self.metadata = {}
        self.is_loaded = False
        
        self._load_model()
        self._initialized = True
    
    def _load_model(self):
        """Load model and explainer from disk."""
        model_path = settings.model_path
        explainer_path = settings.explainer_path
        
        # Check for absolute vs relative path
        base_path = Path(__file__).parent.parent.parent
        
        if not os.path.isabs(model_path):
            model_path = base_path / model_path
            explainer_path = base_path / explainer_path
        
        try:
            if os.path.exists(model_path):
                logger.info(f"Loading model from {model_path}")
                model_data = joblib.load(model_path)
                
                self.model = model_data.get("model")
                self.base_model = model_data.get("base_model")
                self.feature_names = model_data.get("feature_names", [])
                
                logger.info(f"Model loaded with {len(self.feature_names)} features")
            else:
                logger.warning(f"Model not found at {model_path}, using fallback")
                self._create_fallback_model()
            
            if os.path.exists(explainer_path):
                logger.info(f"Loading SHAP explainer from {explainer_path}")
                self.explainer = joblib.load(explainer_path)
            else:
                logger.warning("SHAP explainer not found, explanations will be simulated")
            
            # Load metadata if exists
            metadata_path = str(model_path).replace("risk_model.joblib", "model_metadata.json")
            if os.path.exists(metadata_path):
                with open(metadata_path) as f:
                    self.metadata = json.load(f)
            
            self.is_loaded = True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self._create_fallback_model()
    
    def _create_fallback_model(self):
        """Create a simple fallback model for demo purposes."""
        logger.info("Creating fallback model for demonstration...")
        
        from app.services.feature_engine import FeatureEngineer
        self.feature_names = FeatureEngineer.FEATURE_NAMES
        
        # Simple rule-based fallback
        self.model = None
        self.is_loaded = True
    
    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """
        Predict fraud probability.
        
        Args:
            features: Feature array (n_samples, n_features) or (n_features,)
        
        Returns:
            Probability array [[p_legitimate, p_fraud], ...]
        """
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        if self.model is not None:
            return self.model.predict_proba(features)
        else:
            # Fallback: simple rule-based scoring
            return self._fallback_predict(features)
    
    def _fallback_predict(self, features: np.ndarray) -> np.ndarray:
        """Rule-based fallback prediction when no model is loaded."""
        n_samples = features.shape[0]
        probas = []
        
        for i in range(n_samples):
            f = features[i]
            risk = 0.15  # Base risk
            
            # Get feature indices (fallback to order)
            feature_dict = {name: f[idx] for idx, name in enumerate(self.feature_names)}
            
            # Amount deviation
            amount_zscore = feature_dict.get("amount_zscore", 0)
            if amount_zscore > 2:
                risk += 0.15
            if amount_zscore > 3:
                risk += 0.15
            
            # Country risk
            country_risk = feature_dict.get("country_risk", 0)
            risk += country_risk * 0.2
            
            # New device
            if feature_dict.get("is_new_device", 0) > 0.5:
                risk += 0.1
            
            # Impossible travel
            if feature_dict.get("is_impossible_travel", 0) > 0.5:
                risk += 0.25
            
            # High velocity
            velocity = feature_dict.get("velocity_score", 0)
            risk += velocity * 0.15
            
            # Night transaction
            if feature_dict.get("is_night", 0) > 0.5:
                risk += 0.05
            
            # High risk merchant
            if feature_dict.get("is_high_risk_merchant", 0) > 0.5:
                risk += 0.1
            
            # Behavior anomaly
            risk += feature_dict.get("behavior_anomaly_score", 0) * 0.15
            
            # Clip to valid probability
            risk = max(0.01, min(0.99, risk))
            probas.append([1 - risk, risk])
        
        return np.array(probas)
    
    def get_shap_values(self, features: np.ndarray) -> np.ndarray:
        """
        Calculate SHAP values for features.
        
        Args:
            features: Feature array
        
        Returns:
            SHAP values array
        """
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        if self.explainer is not None:
            try:
                shap_values = self.explainer.shap_values(features)
                # For binary classification, we want the positive class values
                if isinstance(shap_values, list):
                    shap_values = shap_values[1]
                return shap_values
            except Exception as e:
                logger.error(f"Error calculating SHAP values: {e}")
                return self._simulate_shap_values(features)
        else:
            return self._simulate_shap_values(features)
    
    def _simulate_shap_values(self, features: np.ndarray) -> np.ndarray:
        """Simulate SHAP values when no explainer is available."""
        n_samples = features.shape[0]
        n_features = features.shape[1]
        
        # Simple simulation: scale features to simulate impact
        base_impacts = np.array([
            0.05,  # amount
            0.03,  # amount_log
            0.12,  # amount_zscore
            0.04,  # is_round_amount
            0.03,  # amount_percentile
            0.03,  # hour_of_day
            0.02,  # day_of_week
            0.02,  # is_weekend
            0.05,  # is_night
            0.04,  # minutes_since_last_txn
            0.04,  # is_unusual_hour
            0.06,  # txn_count_1h
            0.04,  # txn_count_24h
            0.04,  # amount_sum_1h
            0.03,  # amount_sum_24h
            0.06,  # velocity_score
            0.10,  # country_risk
            0.08,  # distance_from_last_km
            0.06,  # is_new_country
            0.05,  # location_velocity
            0.12,  # is_impossible_travel
            0.08,  # is_new_device
            0.03,  # device_age_days
            0.04,  # device_risk_score
            0.06,  # merchant_category_risk
            0.05,  # is_high_risk_merchant
            0.03,  # user_tenure_days
            0.08,  # user_fraud_history
            0.07,  # amount_vs_avg_ratio
            0.06,  # behavior_anomaly_score
        ])
        
        # Extend or truncate to match feature count
        if len(base_impacts) < n_features:
            base_impacts = np.pad(base_impacts, (0, n_features - len(base_impacts)), constant_values=0.02)
        else:
            base_impacts = base_impacts[:n_features]
        
        shap_values = np.zeros((n_samples, n_features))
        
        for i in range(n_samples):
            # Scale by feature value and add some noise
            shap_values[i] = features[i] * base_impacts * np.random.uniform(0.5, 1.5, n_features)
            # Normalize so it roughly sums to the risk score
            shap_values[i] = shap_values[i] / (np.abs(shap_values[i]).sum() + 1e-6) * 50
        
        return shap_values
    
    def get_expected_value(self) -> float:
        """Get SHAP expected value (base risk)."""
        if self.explainer is not None:
            ev = self.explainer.expected_value
            if isinstance(ev, np.ndarray):
                return float(ev[1] if len(ev) > 1 else ev[0])
            return float(ev)
        return 0.15  # Default base risk
    
    def get_version(self) -> str:
        """Get model version."""
        return self.metadata.get("version", "1.0.0-fallback")


# Singleton instance
model_manager = ModelManager()

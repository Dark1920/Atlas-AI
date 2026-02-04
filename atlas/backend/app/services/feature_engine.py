"""
Feature Engineering Service
Extracts features from transactions for fraud detection model
"""
import math
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import numpy as np
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# Country risk scores (simplified)
COUNTRY_RISK_SCORES = {
    "US": 0.1, "CA": 0.1, "GB": 0.1, "DE": 0.1, "FR": 0.1,
    "AU": 0.1, "JP": 0.1, "NZ": 0.1, "CH": 0.1, "SE": 0.1,
    "NG": 0.8, "RU": 0.7, "CN": 0.5, "BR": 0.5, "IN": 0.4,
    "MX": 0.4, "PH": 0.5, "ID": 0.5, "VN": 0.5, "PK": 0.6,
}

# Merchant category risk scores
MERCHANT_CATEGORY_RISK = {
    "grocery": 0.1, "restaurant": 0.1, "retail": 0.2,
    "electronics": 0.4, "jewelry": 0.5, "cryptocurrency": 0.8,
    "gambling": 0.7, "wire_transfer": 0.6, "atm": 0.3,
    "travel": 0.3, "entertainment": 0.2, "utilities": 0.1,
    "healthcare": 0.1, "education": 0.1, "gas_station": 0.2,
}


@dataclass
class UserProfile:
    """User behavioral profile for feature computation."""
    user_id: str
    avg_amount: float = 100.0
    std_amount: float = 50.0
    avg_txn_per_day: float = 2.0
    total_transactions: int = 0
    common_countries: List[str] = None
    known_devices: List[str] = None
    last_location: tuple = None  # (lat, lon)
    last_transaction_at: datetime = None
    typical_hours: List[int] = None
    fraud_count: int = 0
    
    def __post_init__(self):
        if self.common_countries is None:
            self.common_countries = ["US"]
        if self.known_devices is None:
            self.known_devices = []
        if self.typical_hours is None:
            self.typical_hours = list(range(8, 22))  # 8am-10pm


class FeatureEngineer:
    """
    Feature engineering for fraud detection.
    Extracts ~30 features from transaction data.
    """
    
    # Feature names for model training
    FEATURE_NAMES = [
        # Monetary features
        "amount",
        "amount_log",
        "amount_zscore",
        "is_round_amount",
        "amount_percentile",
        
        # Temporal features
        "hour_of_day",
        "day_of_week",
        "is_weekend",
        "is_night",  # 10pm-6am
        "minutes_since_last_txn",
        "is_unusual_hour",
        
        # Velocity features
        "txn_count_1h",
        "txn_count_24h",
        "amount_sum_1h",
        "amount_sum_24h",
        "velocity_score",
        
        # Location features
        "country_risk",
        "distance_from_last_km",
        "is_new_country",
        "location_velocity",  # distance/time
        "is_impossible_travel",
        
        # Device features
        "is_new_device",
        "device_age_days",
        "device_risk_score",
        
        # Merchant features
        "merchant_category_risk",
        "is_high_risk_merchant",
        
        # User behavior features
        "user_tenure_days",
        "user_fraud_history",
        "amount_vs_avg_ratio",
        "behavior_anomaly_score",
    ]
    
    FEATURE_DISPLAY_NAMES = {
        "amount": "Transaction Amount",
        "amount_log": "Amount (Log Scale)",
        "amount_zscore": "Amount Deviation",
        "is_round_amount": "Round Number",
        "amount_percentile": "Amount Percentile",
        "hour_of_day": "Hour of Day",
        "day_of_week": "Day of Week",
        "is_weekend": "Weekend Transaction",
        "is_night": "Night Transaction",
        "minutes_since_last_txn": "Time Since Last Transaction",
        "is_unusual_hour": "Unusual Hour",
        "txn_count_1h": "Transactions in Last Hour",
        "txn_count_24h": "Transactions in Last 24h",
        "amount_sum_1h": "Amount in Last Hour",
        "amount_sum_24h": "Amount in Last 24h",
        "velocity_score": "Velocity Score",
        "country_risk": "Country Risk",
        "distance_from_last_km": "Distance from Last Location",
        "is_new_country": "New Country",
        "location_velocity": "Location Velocity",
        "is_impossible_travel": "Impossible Travel",
        "is_new_device": "New Device",
        "device_age_days": "Device Age",
        "device_risk_score": "Device Risk",
        "merchant_category_risk": "Merchant Category Risk",
        "is_high_risk_merchant": "High Risk Merchant",
        "user_tenure_days": "Account Age",
        "user_fraud_history": "Fraud History",
        "amount_vs_avg_ratio": "Amount vs Average",
        "behavior_anomaly_score": "Behavior Anomaly",
    }
    
    def __init__(self):
        self._user_profiles: Dict[str, UserProfile] = {}
        self._recent_transactions: Dict[str, List[Dict]] = {}
        # Redis cache will be initialized lazily
        self._cache = None
    
    def _get_cache(self):
        """Get Redis cache instance (lazy initialization)."""
        if self._cache is None:
            from app.services.redis_cache import get_cache
            self._cache = get_cache()
        return self._cache
    
    async def get_user_profile(self, user_id: str) -> UserProfile:
        """Get or create user profile (with Redis caching)."""
        # Try Redis cache first
        cache = self._get_cache()
        cached_profile = await cache.get_user_profile(user_id)
        
        if cached_profile:
            # Reconstruct UserProfile from cache
            profile = UserProfile(
                user_id=cached_profile.get("user_id", user_id),
                avg_amount=cached_profile.get("avg_amount", 100.0),
                std_amount=cached_profile.get("std_amount", 50.0),
                avg_txn_per_day=cached_profile.get("avg_txn_per_day", 2.0),
                total_transactions=cached_profile.get("total_transactions", 0),
                common_countries=cached_profile.get("common_countries", ["US"]),
                known_devices=cached_profile.get("known_devices", []),
                last_location=tuple(cached_profile["last_location"]) if cached_profile.get("last_location") else None,
                last_transaction_at=datetime.fromisoformat(cached_profile["last_transaction_at"]) if cached_profile.get("last_transaction_at") else None,
                typical_hours=cached_profile.get("typical_hours", list(range(8, 22))),
                fraud_count=cached_profile.get("fraud_count", 0),
            )
            # Store in memory cache too
            self._user_profiles[user_id] = profile
            return profile
        
        # Fallback to memory cache
        if user_id not in self._user_profiles:
            self._user_profiles[user_id] = UserProfile(user_id=user_id)
        return self._user_profiles[user_id]
    
    async def update_user_profile(self, user_id: str, transaction: Dict[str, Any]):
        """Update user profile after transaction (with Redis caching)."""
        profile = await self.get_user_profile(user_id)
        cache = self._get_cache()
        
        # Get cached transactions or use memory cache
        cached_txns = await cache.get_recent_transactions(user_id)
        if cached_txns:
            self._recent_transactions[user_id] = cached_txns
        
        # Update transaction history
        if user_id not in self._recent_transactions:
            self._recent_transactions[user_id] = []
        
        txn_data = {
            "amount": transaction.get("amount", 0),
            "timestamp": transaction.get("timestamp", datetime.utcnow()),
            "location": transaction.get("location", {}),
            "device": transaction.get("device", {}),
        }
        
        self._recent_transactions[user_id].append(txn_data)
        
        # Keep only last 100 transactions
        self._recent_transactions[user_id] = self._recent_transactions[user_id][-100:]
        
        # Cache transaction in Redis
        await cache.add_transaction(user_id, txn_data)
        
        # Update profile statistics
        amounts = [t["amount"] for t in self._recent_transactions[user_id]]
        profile.avg_amount = np.mean(amounts)
        profile.std_amount = np.std(amounts) if len(amounts) > 1 else profile.avg_amount * 0.5
        profile.total_transactions = len(self._recent_transactions[user_id])
        
        # Update location
        loc = transaction.get("location", {})
        if loc.get("latitude") and loc.get("longitude"):
            profile.last_location = (loc["latitude"], loc["longitude"])
        
        # Update device
        device = transaction.get("device", {})
        if device.get("fingerprint") and device["fingerprint"] not in profile.known_devices:
            profile.known_devices.append(device["fingerprint"])
        
        # Update country list
        country = loc.get("country")
        if country and country not in profile.common_countries:
            profile.common_countries.append(country)
        
        profile.last_transaction_at = transaction.get("timestamp", datetime.utcnow())
        
        # Cache updated profile in Redis
        await cache.set_user_profile(user_id, {
            "user_id": profile.user_id,
            "avg_amount": profile.avg_amount,
            "std_amount": profile.std_amount,
            "avg_txn_per_day": profile.avg_txn_per_day,
            "total_transactions": profile.total_transactions,
            "common_countries": profile.common_countries,
            "known_devices": profile.known_devices,
            "last_location": list(profile.last_location) if profile.last_location else None,
            "last_transaction_at": profile.last_transaction_at.isoformat() if profile.last_transaction_at else None,
            "typical_hours": profile.typical_hours,
            "fraud_count": profile.fraud_count,
        })
    
    async def extract_features(
        self,
        transaction: Dict[str, Any],
        user_profile: Optional[UserProfile] = None
    ) -> Dict[str, float]:
        """
        Extract all features from a transaction (with Redis caching).
        
        Args:
            transaction: Transaction data dictionary
            user_profile: Optional user profile for behavioral features
        
        Returns:
            Dictionary of feature name -> value
        """
        user_id = transaction.get("user_id", "unknown")
        
        if user_profile is None:
            user_profile = await self.get_user_profile(user_id)
        
        features = {}
        
        # Monetary features
        features.update(self._extract_monetary_features(transaction, user_profile))
        
        # Temporal features
        features.update(self._extract_temporal_features(transaction, user_profile))
        
        # Velocity features (uses Redis cache)
        features.update(await self._extract_velocity_features(transaction, user_id))
        
        # Location features (uses Redis cache for country risk)
        features.update(await self._extract_location_features(transaction, user_profile))
        
        # Device features
        features.update(self._extract_device_features(transaction, user_profile))
        
        # Merchant features (uses Redis cache)
        features.update(await self._extract_merchant_features(transaction))
        
        # User behavior features
        features.update(self._extract_user_behavior_features(transaction, user_profile))
        
        return features
    
    def _extract_monetary_features(
        self,
        transaction: Dict[str, Any],
        profile: UserProfile
    ) -> Dict[str, float]:
        """Extract monetary-related features."""
        amount = float(transaction.get("amount", 0))
        
        # Z-score relative to user's typical spending
        std = profile.std_amount if profile.std_amount > 0 else 1
        zscore = (amount - profile.avg_amount) / std
        
        # Check if round number (common in fraud)
        is_round = 1.0 if amount % 100 == 0 or amount % 50 == 0 else 0.0
        
        # Percentile (simplified - based on assumed distribution)
        percentile = min(1.0, amount / (profile.avg_amount * 10)) if profile.avg_amount > 0 else 0.5
        
        return {
            "amount": amount,
            "amount_log": math.log1p(amount),
            "amount_zscore": min(max(zscore, -10), 10),  # Clip extreme values
            "is_round_amount": is_round,
            "amount_percentile": percentile,
        }
    
    def _extract_temporal_features(
        self,
        transaction: Dict[str, Any],
        profile: UserProfile
    ) -> Dict[str, float]:
        """Extract time-related features."""
        timestamp = transaction.get("timestamp", datetime.utcnow())
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        is_weekend = 1.0 if day_of_week >= 5 else 0.0
        is_night = 1.0 if hour < 6 or hour >= 22 else 0.0
        
        # Time since last transaction
        minutes_since_last = 0.0
        if profile.last_transaction_at:
            delta = timestamp - profile.last_transaction_at
            minutes_since_last = delta.total_seconds() / 60
        
        # Check if unusual hour for user
        is_unusual_hour = 1.0 if hour not in profile.typical_hours else 0.0
        
        return {
            "hour_of_day": float(hour),
            "day_of_week": float(day_of_week),
            "is_weekend": is_weekend,
            "is_night": is_night,
            "minutes_since_last_txn": min(minutes_since_last, 10080),  # Cap at 1 week
            "is_unusual_hour": is_unusual_hour,
        }
    
    async def _extract_velocity_features(
        self,
        transaction: Dict[str, Any],
        user_id: str
    ) -> Dict[str, float]:
        """Extract transaction velocity features (with Redis caching)."""
        timestamp = transaction.get("timestamp", datetime.utcnow())
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        
        # Try Redis cache first
        cache = self._get_cache()
        cached_txns = await cache.get_recent_transactions(user_id)
        if cached_txns:
            self._recent_transactions[user_id] = cached_txns
        
        recent_txns = self._recent_transactions.get(user_id, [])
        
        # Count transactions in last 1h and 24h
        one_hour_ago = timestamp - timedelta(hours=1)
        one_day_ago = timestamp - timedelta(days=1)
        
        txn_count_1h = 0
        txn_count_24h = 0
        amount_sum_1h = 0.0
        amount_sum_24h = 0.0
        
        for txn in recent_txns:
            txn_time = txn.get("timestamp", datetime.utcnow())
            if txn_time >= one_hour_ago:
                txn_count_1h += 1
                amount_sum_1h += txn.get("amount", 0)
            if txn_time >= one_day_ago:
                txn_count_24h += 1
                amount_sum_24h += txn.get("amount", 0)
        
        # Velocity score (normalized)
        velocity_score = min(1.0, (txn_count_1h / 5.0) * 0.5 + (amount_sum_1h / 1000.0) * 0.5)
        
        return {
            "txn_count_1h": float(txn_count_1h),
            "txn_count_24h": float(txn_count_24h),
            "amount_sum_1h": amount_sum_1h,
            "amount_sum_24h": amount_sum_24h,
            "velocity_score": velocity_score,
        }
    
    async def _extract_location_features(
        self,
        transaction: Dict[str, Any],
        profile: UserProfile
    ) -> Dict[str, float]:
        """Extract location-related features (with Redis caching)."""
        location = transaction.get("location", {})
        country = location.get("country", "US")
        lat = location.get("latitude")
        lon = location.get("longitude")
        
        # Country risk (check Redis cache first)
        cache = self._get_cache()
        country_risk = await cache.get_country_risk(country)
        if country_risk is None:
            country_risk = COUNTRY_RISK_SCORES.get(country, 0.5)
            # Cache it for future use
            await cache.set_country_risk(country, country_risk)
        
        # Distance from last known location
        distance_km = 0.0
        location_velocity = 0.0
        is_impossible = 0.0
        
        if lat and lon and profile.last_location:
            last_lat, last_lon = profile.last_location
            distance_km = self._haversine_distance(lat, lon, last_lat, last_lon)
            
            # Check for impossible travel (>1000km in <1 hour)
            if profile.last_transaction_at:
                hours_since = (datetime.utcnow() - profile.last_transaction_at).total_seconds() / 3600
                if hours_since > 0:
                    location_velocity = distance_km / hours_since
                    # Typical commercial flight: ~900 km/h
                    if location_velocity > 1000:
                        is_impossible = 1.0
        
        # Is new country for this user?
        is_new_country = 0.0 if country in profile.common_countries else 1.0
        
        return {
            "country_risk": country_risk,
            "distance_from_last_km": min(distance_km, 20000),  # Cap at half Earth circumference
            "is_new_country": is_new_country,
            "location_velocity": min(location_velocity, 2000),
            "is_impossible_travel": is_impossible,
        }
    
    def _extract_device_features(
        self,
        transaction: Dict[str, Any],
        profile: UserProfile
    ) -> Dict[str, float]:
        """Extract device-related features."""
        device = transaction.get("device", {})
        fingerprint = device.get("fingerprint", "unknown")
        device_type = device.get("type", "desktop")
        
        # Is new device?
        is_new_device = 0.0 if fingerprint in profile.known_devices else 1.0
        
        # Device age (simplified - assume we'd look this up)
        device_age_days = 30.0 if is_new_device == 0.0 else 0.0
        
        # Device risk score (mobile slightly higher risk)
        device_risk = 0.3 if device_type == "mobile" else 0.2
        if is_new_device:
            device_risk += 0.3
        
        return {
            "is_new_device": is_new_device,
            "device_age_days": device_age_days,
            "device_risk_score": device_risk,
        }
    
    async def _extract_merchant_features(self, transaction: Dict[str, Any]) -> Dict[str, float]:
        """Extract merchant-related features (with Redis caching)."""
        category = transaction.get("merchant_category", "retail").lower()
        
        # Check Redis cache first
        cache = self._get_cache()
        category_risk = await cache.get_merchant_risk(category)
        if category_risk is None:
            category_risk = MERCHANT_CATEGORY_RISK.get(category, 0.3)
            # Cache it for future use
            await cache.set_merchant_risk(category, category_risk)
        
        is_high_risk = 1.0 if category_risk >= 0.5 else 0.0
        
        return {
            "merchant_category_risk": category_risk,
            "is_high_risk_merchant": is_high_risk,
        }
    
    def _extract_user_behavior_features(
        self,
        transaction: Dict[str, Any],
        profile: UserProfile
    ) -> Dict[str, float]:
        """Extract user behavioral features."""
        amount = float(transaction.get("amount", 0))
        
        # Account tenure (simplified)
        tenure_days = max(1.0, float(profile.total_transactions))
        
        # Fraud history impact
        fraud_history = min(1.0, profile.fraud_count * 0.2)
        
        # Amount vs average ratio
        avg = profile.avg_amount if profile.avg_amount > 0 else 100
        amount_ratio = amount / avg
        
        # Behavior anomaly score (composite)
        anomaly_score = 0.0
        if amount_ratio > 3:
            anomaly_score += 0.3
        if profile.total_transactions < 5:
            anomaly_score += 0.2
        if fraud_history > 0:
            anomaly_score += fraud_history
        
        return {
            "user_tenure_days": min(tenure_days, 365),
            "user_fraud_history": fraud_history,
            "amount_vs_avg_ratio": min(amount_ratio, 100),
            "behavior_anomaly_score": min(anomaly_score, 1.0),
        }
    
    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in km using Haversine formula."""
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def get_feature_vector(self, features: Dict[str, float]) -> np.ndarray:
        """Convert feature dictionary to numpy array for model input."""
        return np.array([features.get(name, 0.0) for name in self.FEATURE_NAMES])
    
    def get_feature_display_name(self, feature_name: str) -> str:
        """Get human-readable display name for a feature."""
        return self.FEATURE_DISPLAY_NAMES.get(feature_name, feature_name.replace("_", " ").title())

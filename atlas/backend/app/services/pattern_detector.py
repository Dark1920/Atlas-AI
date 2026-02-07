"""
Pattern Detection Service
Detects fraud patterns and fraud rings across transactions
Inspired by Deriv's ThreatHunter system
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class FraudPattern:
    """Represents a detected fraud pattern."""
    
    def __init__(
        self,
        pattern_id: str,
        pattern_type: str,
        description: str,
        confidence: float,
        affected_transactions: List[str],
        affected_users: List[str],
        metadata: Dict[str, Any]
    ):
        self.id = pattern_id
        self.pattern_type = pattern_type
        self.description = description
        self.confidence = confidence
        self.affected_transactions = affected_transactions
        self.affected_users = affected_users
        self.metadata = metadata
        self.detected_at = datetime.utcnow()


class PatternDetector:
    """
    Detects fraud patterns and fraud rings.
    Inspired by Deriv's ThreatHunter for proactive threat detection.
    """
    
    def __init__(self):
        self._detected_patterns: Dict[str, FraudPattern] = {}
        self._pattern_history: List[FraudPattern] = []
    
    def detect_patterns(
        self,
        transactions: List[Dict[str, Any]],
        risk_assessments: Dict[str, Dict[str, Any]]
    ) -> List[FraudPattern]:
        """
        Detect fraud patterns from a set of transactions.
        
        Args:
            transactions: List of transaction dictionaries
            risk_assessments: Dict mapping transaction_id to risk assessment
        
        Returns:
            List of detected fraud patterns
        """
        patterns = []
        
        # Detect fraud rings (multiple users, same device/merchant)
        fraud_rings = self._detect_fraud_rings(transactions, risk_assessments)
        patterns.extend(fraud_rings)
        
        # Detect velocity patterns (rapid transactions)
        velocity_patterns = self._detect_velocity_patterns(transactions, risk_assessments)
        patterns.extend(velocity_patterns)
        
        # Detect location patterns (impossible travel clusters)
        location_patterns = self._detect_location_patterns(transactions, risk_assessments)
        patterns.extend(location_patterns)
        
        # Detect merchant patterns (suspicious merchant clusters)
        merchant_patterns = self._detect_merchant_patterns(transactions, risk_assessments)
        patterns.extend(merchant_patterns)
        
        # Store patterns
        for pattern in patterns:
            self._detected_patterns[pattern.id] = pattern
            self._pattern_history.append(pattern)
        
        # Keep only last 500 patterns
        if len(self._pattern_history) > 500:
            self._pattern_history = self._pattern_history[-500:]
        
        return patterns
    
    def _detect_fraud_rings(
        self,
        transactions: List[Dict[str, Any]],
        risk_assessments: Dict[str, Dict[str, Any]]
    ) -> List[FraudPattern]:
        """
        Detect fraud rings: multiple users using same device/merchant.
        """
        patterns = []
        
        # Group by device fingerprint
        device_to_users: Dict[str, Set[str]] = defaultdict(set)
        device_to_txns: Dict[str, List[str]] = defaultdict(list)
        
        # Group by merchant
        merchant_to_users: Dict[str, Set[str]] = defaultdict(set)
        merchant_to_txns: Dict[str, List[str]] = defaultdict(list)
        
        for txn in transactions:
            txn_id = txn.get("transaction_id")
            user_id = txn.get("user_id")
            device_fp = txn.get("device", {}).get("fingerprint")
            merchant_id = txn.get("merchant_id")
            risk_score = risk_assessments.get(txn_id, {}).get("risk_score", 0)
            
            # Only consider high-risk transactions
            if risk_score < 60:
                continue
            
            if device_fp:
                device_to_users[device_fp].add(user_id)
                device_to_txns[device_fp].append(txn_id)
            
            if merchant_id:
                merchant_to_users[merchant_id].add(user_id)
                merchant_to_txns[merchant_id].append(txn_id)
        
        # Detect device-based fraud rings
        for device_fp, users in device_to_users.items():
            if len(users) >= 3:  # 3+ users on same device
                txns = device_to_txns[device_fp]
                if len(txns) >= 3:
                    pattern_id = f"ring_device_{uuid.uuid4().hex[:12]}"
                    confidence = min(0.9, 0.5 + (len(users) - 3) * 0.1)
                    
                    pattern = FraudPattern(
                        pattern_id=pattern_id,
                        pattern_type="fraud_ring_device",
                        description=f"Fraud ring detected: {len(users)} users sharing device {device_fp[:8]}...",
                        confidence=confidence,
                        affected_transactions=txns,
                        affected_users=list(users),
                        metadata={
                            "device_fingerprint": device_fp,
                            "user_count": len(users),
                            "transaction_count": len(txns),
                        }
                    )
                    patterns.append(pattern)
        
        # Detect merchant-based fraud rings
        for merchant_id, users in merchant_to_users.items():
            if len(users) >= 5:  # 5+ users at same merchant
                txns = merchant_to_txns[merchant_id]
                if len(txns) >= 5:
                    pattern_id = f"ring_merchant_{uuid.uuid4().hex[:12]}"
                    confidence = min(0.85, 0.4 + (len(users) - 5) * 0.05)
                    
                    pattern = FraudPattern(
                        pattern_id=pattern_id,
                        pattern_type="fraud_ring_merchant",
                        description=f"Fraud ring detected: {len(users)} users at merchant {merchant_id}",
                        confidence=confidence,
                        affected_transactions=txns,
                        affected_users=list(users),
                        metadata={
                            "merchant_id": merchant_id,
                            "user_count": len(users),
                            "transaction_count": len(txns),
                        }
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _detect_velocity_patterns(
        self,
        transactions: List[Dict[str, Any]],
        risk_assessments: Dict[str, Dict[str, Any]]
    ) -> List[FraudPattern]:
        """Detect velocity-based fraud patterns."""
        patterns = []
        
        # Group transactions by user
        user_txns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        for txn in transactions:
            user_id = txn.get("user_id")
            if user_id:
                user_txns[user_id].append(txn)
        
        # Check for rapid transaction patterns
        for user_id, txns in user_txns.items():
            if len(txns) < 5:
                continue
            
            # Sort by timestamp
            txns_sorted = sorted(
                txns,
                key=lambda t: t.get("timestamp", datetime.utcnow())
            )
            
            # Check for burst pattern (many transactions in short time)
            for i in range(len(txns_sorted) - 4):
                window = txns_sorted[i:i+5]
                timestamps = [
                    t.get("timestamp", datetime.utcnow())
                    for t in window
                ]
                
                # Check if all within 1 hour
                time_span = (timestamps[-1] - timestamps[0]).total_seconds() / 3600
                if time_span <= 1.0:
                    # Check risk scores
                    high_risk_count = sum(
                        1 for t in window
                        if risk_assessments.get(t.get("transaction_id"), {}).get("risk_score", 0) >= 60
                    )
                    
                    if high_risk_count >= 3:
                        pattern_id = f"velocity_{uuid.uuid4().hex[:12]}"
                        txn_ids = [t.get("transaction_id") for t in window]
                        
                        pattern = FraudPattern(
                            pattern_id=pattern_id,
                            pattern_type="velocity_burst",
                            description=f"Velocity burst: {len(window)} transactions in {time_span:.1f} hours",
                            confidence=0.75,
                            affected_transactions=txn_ids,
                            affected_users=[user_id],
                            metadata={
                                "time_span_hours": time_span,
                                "transaction_count": len(window),
                                "high_risk_count": high_risk_count,
                            }
                        )
                        patterns.append(pattern)
                        break  # Only one pattern per user
        
        return patterns
    
    def _detect_location_patterns(
        self,
        transactions: List[Dict[str, Any]],
        risk_assessments: Dict[str, Dict[str, Any]]
    ) -> List[FraudPattern]:
        """Detect location-based fraud patterns."""
        patterns = []
        
        # Group by user
        user_locations: Dict[str, List[Tuple[datetime, str, float, float]]] = defaultdict(list)
        
        for txn in transactions:
            user_id = txn.get("user_id")
            location = txn.get("location", {})
            country = location.get("country")
            lat = location.get("latitude")
            lon = location.get("longitude")
            timestamp = txn.get("timestamp", datetime.utcnow())
            
            if user_id and country and lat and lon:
                user_locations[user_id].append((timestamp, country, lat, lon))
        
        # Check for impossible travel patterns
        for user_id, locations in user_locations.items():
            if len(locations) < 2:
                continue
            
            locations_sorted = sorted(locations, key=lambda x: x[0])
            
            for i in range(len(locations_sorted) - 1):
                time1, country1, lat1, lon1 = locations_sorted[i]
                time2, country2, lat2, lon2 = locations_sorted[i + 1]
                
                # Calculate distance
                distance_km = self._haversine_distance(lat1, lon1, lat2, lon2)
                time_diff_hours = (time2 - time1).total_seconds() / 3600
                
                # Impossible travel: >1000km in <2 hours
                if time_diff_hours < 2 and distance_km > 1000:
                    txn_ids = [
                        t.get("transaction_id")
                        for t in transactions
                        if t.get("user_id") == user_id
                        and (
                            (t.get("location", {}).get("latitude") == lat1 and t.get("location", {}).get("longitude") == lon1)
                            or (t.get("location", {}).get("latitude") == lat2 and t.get("location", {}).get("longitude") == lon2)
                        )
                    ]
                    
                    if txn_ids:
                        pattern_id = f"location_{uuid.uuid4().hex[:12]}"
                        
                        pattern = FraudPattern(
                            pattern_id=pattern_id,
                            pattern_type="impossible_travel",
                            description=f"Impossible travel: {distance_km:.0f}km in {time_diff_hours:.1f}h",
                            confidence=0.9,
                            affected_transactions=txn_ids,
                            affected_users=[user_id],
                            metadata={
                                "distance_km": distance_km,
                                "time_hours": time_diff_hours,
                                "from_country": country1,
                                "to_country": country2,
                            }
                        )
                        patterns.append(pattern)
        
        return patterns
    
    def _detect_merchant_patterns(
        self,
        transactions: List[Dict[str, Any]],
        risk_assessments: Dict[str, Dict[str, Any]]
    ) -> List[FraudPattern]:
        """Detect suspicious merchant patterns."""
        patterns = []
        
        # Group by merchant category
        category_txns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        for txn in transactions:
            category = txn.get("merchant_category")
            risk_score = risk_assessments.get(txn.get("transaction_id"), {}).get("risk_score", 0)
            
            if category and risk_score >= 60:
                category_txns[category].append(txn)
        
        # Check for high-risk merchant clusters
        for category, txns in category_txns.items():
            if len(txns) >= 10:  # 10+ high-risk transactions
                # Check if from multiple users (potential coordinated attack)
                users = set(t.get("user_id") for t in txns)
                
                if len(users) >= 3:
                    pattern_id = f"merchant_{uuid.uuid4().hex[:12]}"
                    txn_ids = [t.get("transaction_id") for t in txns]
                    
                    pattern = FraudPattern(
                        pattern_id=pattern_id,
                        pattern_type="suspicious_merchant_cluster",
                        description=f"Suspicious cluster: {len(txns)} high-risk transactions at {category}",
                        confidence=0.7,
                        affected_transactions=txn_ids,
                        affected_users=list(users),
                        metadata={
                            "merchant_category": category,
                            "transaction_count": len(txns),
                            "user_count": len(users),
                        }
                    )
                    patterns.append(pattern)
        
        return patterns
    
    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in km."""
        import math
        
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def get_pattern(self, pattern_id: str) -> Optional[FraudPattern]:
        """Get pattern by ID."""
        return self._detected_patterns.get(pattern_id)
    
    def get_all_patterns(
        self,
        pattern_type: Optional[str] = None,
        limit: int = 100
    ) -> List[FraudPattern]:
        """Get all detected patterns."""
        patterns = list(self._detected_patterns.values())
        
        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]
        
        # Sort by detected_at (newest first)
        patterns.sort(key=lambda x: x.detected_at, reverse=True)
        
        return patterns[:limit]


# Singleton instance
_pattern_detector_instance: Optional[PatternDetector] = None


def get_pattern_detector() -> PatternDetector:
    """Get pattern detector singleton instance."""
    global _pattern_detector_instance
    if _pattern_detector_instance is None:
        _pattern_detector_instance = PatternDetector()
    return _pattern_detector_instance

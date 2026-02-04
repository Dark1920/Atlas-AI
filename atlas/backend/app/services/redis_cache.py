"""
Redis Cache Service
Provides caching layer for user profiles, transactions, and API responses
Inspired by Deriv's optimized infrastructure
"""
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
try:
    import redis.asyncio as aioredis
except ImportError:
    # Fallback for older redis versions
    try:
        import aioredis
    except ImportError:
        aioredis = None
from functools import wraps

from app.config import settings

logger = logging.getLogger(__name__)

# Global Redis connection pool
_redis_client: Optional[aioredis.Redis] = None


async def get_redis_client():
    """Get or create Redis client connection."""
    global _redis_client
    if aioredis is None:
        logger.warning("Redis async client not available. Install redis>=5.0.0")
        return None
    
    if _redis_client is None:
        try:
            _redis_client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )
            # Test connection
            await _redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Return None for graceful degradation
            _redis_client = None
    
    return _redis_client


class RedisCache:
    """
    Redis caching service for Atlas-AI.
    Caches user profiles, transaction velocity, and risk scores.
    """
    
    # Cache key prefixes
    KEY_PREFIX_USER_PROFILE = "user:profile:"
    KEY_PREFIX_USER_TXNS = "user:txns:"
    KEY_PREFIX_COUNTRY_RISK = "risk:country:"
    KEY_PREFIX_MERCHANT_RISK = "risk:merchant:"
    KEY_PREFIX_API_RESPONSE = "api:response:"
    
    def __init__(self):
        self.default_ttl = settings.cache_ttl
        self._client: Optional[aioredis.Redis] = None
    
    async def _get_client(self) -> Optional[aioredis.Redis]:
        """Get Redis client, return None if unavailable."""
        if self._client is None:
            self._client = await get_redis_client()
        return self._client
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached user profile.
        
        Args:
            user_id: User ID
            
        Returns:
            User profile dict or None if not cached
        """
        client = await self._get_client()
        if not client:
            return None
        
        try:
            key = f"{self.KEY_PREFIX_USER_PROFILE}{user_id}"
            data = await client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Error getting user profile from cache: {e}")
        
        return None
    
    async def set_user_profile(
        self,
        user_id: str,
        profile: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache user profile.
        
        Args:
            user_id: User ID
            profile: User profile dictionary
            ttl: Time to live in seconds (defaults to settings.cache_ttl)
            
        Returns:
            True if cached successfully
        """
        client = await self._get_client()
        if not client:
            return False
        
        try:
            key = f"{self.KEY_PREFIX_USER_PROFILE}{user_id}"
            ttl = ttl or self.default_ttl
            await client.setex(
                key,
                ttl,
                json.dumps(profile, default=str)
            )
            return True
        except Exception as e:
            logger.warning(f"Error caching user profile: {e}")
            return False
    
    async def get_recent_transactions(
        self,
        user_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get cached recent transactions for velocity features.
        
        Args:
            user_id: User ID
            limit: Maximum number of transactions to return
            
        Returns:
            List of transaction dictionaries
        """
        client = await self._get_client()
        if not client:
            return []
        
        try:
            key = f"{self.KEY_PREFIX_USER_TXNS}{user_id}"
            # Use sorted set with timestamp as score
            data = await client.zrevrange(key, 0, limit - 1, withscores=False)
            transactions = []
            for item in data:
                try:
                    transactions.append(json.loads(item))
                except:
                    continue
            return transactions
        except Exception as e:
            logger.warning(f"Error getting transactions from cache: {e}")
            return []
    
    async def add_transaction(
        self,
        user_id: str,
        transaction: Dict[str, Any],
        max_items: int = 100
    ) -> bool:
        """
        Add transaction to cache for velocity features.
        
        Args:
            user_id: User ID
            transaction: Transaction dictionary
            max_items: Maximum items to keep in cache
            
        Returns:
            True if added successfully
        """
        client = await self._get_client()
        if not client:
            return False
        
        try:
            key = f"{self.KEY_PREFIX_USER_TXNS}{user_id}"
            timestamp = transaction.get("timestamp", datetime.utcnow())
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            elif isinstance(timestamp, datetime):
                pass
            else:
                timestamp = datetime.utcnow()
            
            # Use timestamp as score for sorted set
            score = timestamp.timestamp()
            value = json.dumps(transaction, default=str)
            
            # Add to sorted set
            await client.zadd(key, {value: score})
            
            # Trim to max_items
            await client.zremrangebyrank(key, 0, -(max_items + 1))
            
            # Set expiration
            await client.expire(key, self.default_ttl * 2)  # Longer TTL for transaction history
            
            return True
        except Exception as e:
            logger.warning(f"Error caching transaction: {e}")
            return False
    
    async def get_country_risk(self, country: str) -> Optional[float]:
        """
        Get cached country risk score.
        
        Args:
            country: Country code
            
        Returns:
            Risk score or None
        """
        client = await self._get_client()
        if not client:
            return None
        
        try:
            key = f"{self.KEY_PREFIX_COUNTRY_RISK}{country}"
            value = await client.get(key)
            if value:
                return float(value)
        except Exception as e:
            logger.warning(f"Error getting country risk from cache: {e}")
        
        return None
    
    async def set_country_risk(
        self,
        country: str,
        risk_score: float,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache country risk score.
        
        Args:
            country: Country code
            risk_score: Risk score (0-1)
            ttl: Time to live in seconds
            
        Returns:
            True if cached successfully
        """
        client = await self._get_client()
        if not client:
            return False
        
        try:
            key = f"{self.KEY_PREFIX_COUNTRY_RISK}{country}"
            ttl = ttl or (self.default_ttl * 24)  # 24x longer TTL for static data
            await client.setex(key, ttl, str(risk_score))
            return True
        except Exception as e:
            logger.warning(f"Error caching country risk: {e}")
            return False
    
    async def get_merchant_risk(self, merchant_category: str) -> Optional[float]:
        """
        Get cached merchant category risk score.
        
        Args:
            merchant_category: Merchant category
            
        Returns:
            Risk score or None
        """
        client = await self._get_client()
        if not client:
            return None
        
        try:
            key = f"{self.KEY_PREFIX_MERCHANT_RISK}{merchant_category}"
            value = await client.get(key)
            if value:
                return float(value)
        except Exception as e:
            logger.warning(f"Error getting merchant risk from cache: {e}")
        
        return None
    
    async def set_merchant_risk(
        self,
        merchant_category: str,
        risk_score: float,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache merchant category risk score.
        
        Args:
            merchant_category: Merchant category
            risk_score: Risk score (0-1)
            ttl: Time to live in seconds
            
        Returns:
            True if cached successfully
        """
        client = await self._get_client()
        if not client:
            return False
        
        try:
            key = f"{self.KEY_PREFIX_MERCHANT_RISK}{merchant_category}"
            ttl = ttl or (self.default_ttl * 24)  # 24x longer TTL for static data
            await client.setex(key, ttl, str(risk_score))
            return True
        except Exception as e:
            logger.warning(f"Error caching merchant risk: {e}")
            return False
    
    async def get_api_response(self, cache_key: str) -> Optional[Any]:
        """
        Get cached API response.
        
        Args:
            cache_key: Cache key for the response
            
        Returns:
            Cached response or None
        """
        client = await self._get_client()
        if not client:
            return None
        
        try:
            key = f"{self.KEY_PREFIX_API_RESPONSE}{cache_key}"
            data = await client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Error getting API response from cache: {e}")
        
        return None
    
    async def set_api_response(
        self,
        cache_key: str,
        response: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache API response.
        
        Args:
            cache_key: Cache key for the response
            response: Response data to cache
            ttl: Time to live in seconds
            
        Returns:
            True if cached successfully
        """
        client = await self._get_client()
        if not client:
            return False
        
        try:
            key = f"{self.KEY_PREFIX_API_RESPONSE}{cache_key}"
            ttl = ttl or self.default_ttl
            await client.setex(
                key,
                ttl,
                json.dumps(response, default=str)
            )
            return True
        except Exception as e:
            logger.warning(f"Error caching API response: {e}")
            return False
    
    async def invalidate_user_cache(self, user_id: str) -> bool:
        """
        Invalidate all cache entries for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if invalidated successfully
        """
        client = await self._get_client()
        if not client:
            return False
        
        try:
            profile_key = f"{self.KEY_PREFIX_USER_PROFILE}{user_id}"
            txns_key = f"{self.KEY_PREFIX_USER_TXNS}{user_id}"
            await client.delete(profile_key, txns_key)
            return True
        except Exception as e:
            logger.warning(f"Error invalidating user cache: {e}")
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        client = await self._get_client()
        if not client:
            return {
                "enabled": False,
                "hit_rate": 0.0,
                "keys": 0
            }
        
        try:
            info = await client.info("stats")
            keyspace = await client.info("keyspace")
            
            # Calculate hit rate
            hits = int(info.get("keyspace_hits", 0))
            misses = int(info.get("keyspace_misses", 0))
            total = hits + misses
            hit_rate = (hits / total * 100) if total > 0 else 0.0
            
            # Count keys
            db_info = keyspace.get("db0", {})
            keys = int(db_info.get("keys", 0))
            
            return {
                "enabled": True,
                "hit_rate": round(hit_rate, 2),
                "keys": keys,
                "hits": hits,
                "misses": misses
            }
        except Exception as e:
            logger.warning(f"Error getting cache stats: {e}")
            return {
                "enabled": False,
                "error": str(e)
            }


# Singleton instance
_cache_instance: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """Get Redis cache singleton instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance

"""
API Authentication
API key authentication middleware for securing endpoints
Inspired by Deriv's zero-trust security
"""
import secrets
from datetime import datetime
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# API Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# In-memory API keys (in production, store in database)
# Format: {api_key: {"name": "key_name", "enabled": True, "scopes": ["score", "read"]}}
_api_keys: dict[str, dict] = {}

# Default API key for development (should be changed in production)
DEFAULT_API_KEY = "atlas_dev_key_" + secrets.token_urlsafe(16)


def initialize_api_keys():
    """Initialize default API keys."""
    global _api_keys
    if not _api_keys:
        # Create default API key
        _api_keys[DEFAULT_API_KEY] = {
            "name": "Default Development Key",
            "enabled": True,
            "scopes": ["score", "read", "write"],
            "created_at": "2024-01-01T00:00:00Z"
        }
        logger.info("API keys initialized with default development key")


def create_api_key(name: str, scopes: list[str] = None) -> str:
    """
    Create a new API key.
    
    Args:
        name: Key name/description
        scopes: List of allowed scopes
    
    Returns:
        Generated API key
    """
    api_key = "atlas_" + secrets.token_urlsafe(32)
    _api_keys[api_key] = {
        "name": name,
        "enabled": True,
        "scopes": scopes or ["score", "read"],
        "created_at": datetime.utcnow().isoformat()
    }
    logger.info(f"Created API key: {name}")
    return api_key


def validate_api_key(api_key: Optional[str] = None) -> dict:
    """
    Validate API key.
    
    Args:
        api_key: API key to validate
    
    Returns:
        Key metadata if valid
    
    Raises:
        HTTPException if invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    key_info = _api_keys.get(api_key)
    
    if not key_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if not key_info.get("enabled", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key is disabled",
        )
    
    return key_info


def require_api_key(required_scope: Optional[str] = None):
    """
    Dependency for API key authentication.
    
    Args:
        required_scope: Required scope (e.g., "score", "read")
    
    Returns:
        Key metadata
    """
    async def get_api_key(api_key: Optional[str] = Security(api_key_header)) -> dict:
        key_info = validate_api_key(api_key)
        
        if required_scope:
            scopes = key_info.get("scopes", [])
            if required_scope not in scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"API key does not have required scope: {required_scope}",
                )
        
        return key_info
    
    return get_api_key


def get_api_key_info(api_key: str) -> Optional[dict]:
    """Get API key information."""
    return _api_keys.get(api_key)


def list_api_keys() -> list[dict]:
    """List all API keys (without exposing full keys)."""
    return [
        {
            "name": info["name"],
            "enabled": info.get("enabled", True),
            "scopes": info.get("scopes", []),
            "created_at": info.get("created_at"),
            "key_prefix": key[:10] + "..." if len(key) > 10 else key,
        }
        for key, info in _api_keys.items()
    ]


def disable_api_key(api_key: str) -> bool:
    """Disable an API key."""
    if api_key in _api_keys:
        _api_keys[api_key]["enabled"] = False
        logger.info(f"Disabled API key: {_api_keys[api_key].get('name')}")
        return True
    return False


def enable_api_key(api_key: str) -> bool:
    """Enable an API key."""
    if api_key in _api_keys:
        _api_keys[api_key]["enabled"] = True
        logger.info(f"Enabled API key: {_api_keys[api_key].get('name')}")
        return True
    return False


# Initialize on import
initialize_api_keys()

"""
JWT Authentication
JWT-based authentication for dashboard users
Inspired by Deriv's secure authentication systems
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import secrets

# JWT settings
SECRET_KEY = secrets.token_urlsafe(32)  # In production, use env variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# In-memory user store (in production, use database)
# Format: {username: {"username": str, "password": str, "role": str, "enabled": bool}}
_users: dict[str, dict] = {
    "admin": {
        "username": "admin",
        "password": "admin123",  # Change in production!
        "role": "admin",
        "enabled": True,
    },
    "analyst": {
        "username": "analyst",
        "password": "analyst123",  # Change in production!
        "role": "analyst",
        "enabled": True,
    },
}

# Pre-hashed passwords cache to avoid repeated hashing on startup
_precomputed_hashes: dict[str, str] = {}


class User(BaseModel):
    """User model."""
    username: str
    role: str
    enabled: bool


class Token(BaseModel):
    """Token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data."""
    username: Optional[str] = None
    role: Optional[str] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def get_user(username: str) -> Optional[dict]:
    """Get user by username."""
    user_data = _users.get(username)
    if user_data and user_data.get("hashed_password"):
        return user_data
    
    # If user exists but doesn't have precomputed hash, compute it
    if user_data and "password" in user_data:
        # Compute and cache the hash
        password_to_hash = user_data["password"]
        if username not in _precomputed_hashes:
            _precomputed_hashes[username] = pwd_context.hash(password_to_hash[:72])  # Limit to 72 chars
        # Return user data with hashed password
        return {
            "username": user_data["username"],
            "hashed_password": _precomputed_hashes[username],
            "role": user_data["role"],
            "enabled": user_data["enabled"]
        }
    
    return user_data


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate a user."""
    user = get_user(username)
    if not user:
        return None
    
    if not user.get("enabled", True):
        return None
    
    if not verify_password(password, user["hashed_password"]):
        return None
    
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role", "analyst")
        
        if username is None:
            raise credentials_exception
        
    except JWTError:
        raise credentials_exception
    
    user = get_user(username)
    if user is None:
        raise credentials_exception
    
    if not user.get("enabled", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return User(
        username=user["username"],
        role=user["role"],
        enabled=user["enabled"]
    )


async def require_role(required_role: str):
    """Dependency to require a specific role."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role} role"
            )
        return current_user
    
    return role_checker

"""
Dependency Injection

FastAPI dependencies for database sessions, Redis connections,
authentication, and service instances.
"""

from typing import AsyncGenerator, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import verify_token
from app.db.session import get_db
from app.db.redis_client import get_redis_client
from app.services.inbox_service import InboxService
from app.services.message_service import MessageService
from app.services.encryption_service import EncryptionService
from app.services.sanitization_service import SanitizationService


settings = get_settings()


# ===================================
# Database Dependencies
# ===================================

async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session.
    
    Yields:
        AsyncSession: SQLAlchemy async session
    """
    async for session in get_db():
        yield session


# ===================================
# Redis Dependencies
# ===================================

async def get_redis():
    """
    Get Redis client.
    
    Returns:
        Redis: Redis client instance
    """
    return await get_redis_client()


# ===================================
# Service Dependencies
# ===================================

def get_encryption_service() -> EncryptionService:
    """
    Get encryption service instance.
    
    Returns:
        EncryptionService: Encryption service
    """
    return EncryptionService()


def get_sanitization_service() -> SanitizationService:
    """
    Get sanitization service instance.
    
    Returns:
        SanitizationService: Sanitization service
    """
    return SanitizationService()


def get_inbox_service(
    db: AsyncSession = Depends(get_database),
    redis = Depends(get_redis),
    encryption: EncryptionService = Depends(get_encryption_service),
) -> InboxService:
    """
    Get inbox service instance.
    
    Args:
        db: Database session
        redis: Redis client
        encryption: Encryption service
    
    Returns:
        InboxService: Inbox service
    """
    return InboxService(db, redis, encryption)


def get_message_service(
    db: AsyncSession = Depends(get_database),
    redis = Depends(get_redis),
    encryption: EncryptionService = Depends(get_encryption_service),
    sanitization: SanitizationService = Depends(get_sanitization_service),
) -> MessageService:
    """
    Get message service instance.
    
    Args:
        db: Database session
        redis: Redis client
        encryption: Encryption service
        sanitization: Sanitization service
    
    Returns:
        MessageService: Message service
    """
    return MessageService(db, redis, encryption, sanitization)


# ===================================
# Authentication Dependencies
# ===================================

async def get_current_inbox(
    authorization: Optional[str] = Header(None),
    inbox_service: InboxService = Depends(get_inbox_service),
) -> str:
    """
    Verify inbox token and return inbox ID.
    
    Args:
        authorization: Authorization header (Bearer token)
        inbox_service: Inbox service
    
    Returns:
        str: Inbox ID
    
    Raises:
        HTTPException: If token is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract token
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authentication scheme")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify token
    try:
        payload = verify_token(token)
        inbox_id = payload.get("inbox_id")
        
        if not inbox_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        
        # Verify inbox still exists
        inbox = await inbox_service.get_inbox(inbox_id)
        if not inbox:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inbox not found or expired",
            )
        
        return inbox_id
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> bool:
    """
    Verify API key for admin endpoints.
    
    Args:
        x_api_key: API key from header
    
    Returns:
        bool: True if valid
    
    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "API-Key"},
        )
    
    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    
    return True


# ===================================
# Rate Limiting Dependencies
# ===================================

async def check_rate_limit(
    request: Request,
    redis = Depends(get_redis),
) -> bool:
    """
    Check rate limit for the current request.
    
    Args:
        request: FastAPI request
        redis: Redis client
    
    Returns:
        bool: True if within limits
    
    Raises:
        HTTPException: If rate limit exceeded
    """
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Rate limit keys
    minute_key = f"ratelimit:minute:{client_ip}"
    hour_key = f"ratelimit:hour:{client_ip}"
    
    # Check minute limit
    minute_count = await redis.get(minute_key)
    if minute_count and int(minute_count) >= settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": "60"},
        )
    
    # Check hour limit
    hour_count = await redis.get(hour_key)
    if hour_count and int(hour_count) >= settings.RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Hourly rate limit exceeded. Please try again later.",
            headers={"Retry-After": "3600"},
        )
    
    # Increment counters
    pipe = redis.pipeline()
    pipe.incr(minute_key)
    pipe.expire(minute_key, 60)
    pipe.incr(hour_key)
    pipe.expire(hour_key, 3600)
    await pipe.execute()
    
    return True


async def check_inbox_creation_limit(
    request: Request,
    redis = Depends(get_redis),
) -> bool:
    """
    Check inbox creation rate limit.
    
    Args:
        request: FastAPI request
        redis: Redis client
    
    Returns:
        bool: True if within limits
    
    Raises:
        HTTPException: If rate limit exceeded
    """
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Inbox creation limit key
    key = f"inbox_creation:hour:{client_ip}"
    
    # Check limit
    count = await redis.get(key)
    if count and int(count) >= settings.INBOX_CREATION_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Inbox creation limit exceeded. Please try again later.",
            headers={"Retry-After": "3600"},
        )
    
    # Increment counter
    await redis.incr(key)
    await redis.expire(key, 3600)
    
    return True
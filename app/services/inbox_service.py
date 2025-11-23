"""
Inbox Service

Business logic for inbox management:
- Creation with unique address generation
- Token generation and validation
- TTL management
- Quota enforcement
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import create_access_token, generate_inbox_address, generate_inbox_id, hash_password
from app.core.exceptions import InboxNotFoundException, InboxExpiredException, QuotaExceededException
from app.core.logging import get_logger
from app.core.metrics import record_inbox_created
from app.db.models import Inbox
from app.schemas.inbox import InboxResponse

settings = get_settings()
logger = get_logger(__name__)


class InboxService:
    """Service for managing temporary inboxes."""
    
    def __init__(self, db: AsyncSession, redis, encryption):
        self.db = db
        self.redis = redis
        self.encryption = encryption
    
    async def create_inbox(self, ttl_hours: Optional[int] = None) -> InboxResponse:
        """
        Create a new temporary inbox.
        
        Args:
            ttl_hours: Time-to-live in hours (default from settings)
        
        Returns:
            InboxResponse: Created inbox details with access token
        
        Raises:
            DatabaseException: If database operation fails
        """
        ttl = ttl_hours or settings.DEFAULT_TTL_HOURS
        
        # Generate unique inbox ID and address
        inbox_id = generate_inbox_id()
        address = generate_inbox_address(
            domain=settings.APP_DOMAIN,
            prefix=settings.ADDRESS_PREFIX,
            length=settings.ADDRESS_LENGTH,
        )
        
        # Ensure address is unique
        retries = 0
        while await self._address_exists(address) and retries < 5:
            address = generate_inbox_address(
                domain=settings.APP_DOMAIN,
                prefix=settings.ADDRESS_PREFIX,
                length=settings.ADDRESS_LENGTH,
            )
            retries += 1
        
        # Generate access token
        token_data = {
            "inbox_id": str(inbox_id),
            "address": address,
        }
        token = create_access_token(
            data=token_data,
            expires_delta=timedelta(hours=ttl),
        )
        
        # Hash token for storage
        token_hash = hash_password(token)
        
        # Calculate expiration
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=ttl)
        
        # Create inbox in database
        inbox = Inbox(
            id=inbox_id,
            address=address,
            token_hash=token_hash,
            created_at=now,
            expires_at=expires_at,
            is_active=True,
            message_count=0,
        )
        
        self.db.add(inbox)
        await self.db.commit()
        await self.db.refresh(inbox)
        
        # Store in Redis with TTL for fast lookup
        ttl_seconds = ttl * 3600
        await self.redis.setex(
            f"inbox:{address}",
            ttl_seconds,
            str(inbox_id),
        )
        await self.redis.setex(
            f"inbox:id:{inbox_id}",
            ttl_seconds,
            address,
        )
        
        # Record metrics
        record_inbox_created()
        
        logger.info(f"Created inbox: {address} (TTL: {ttl}h)")
        
        return InboxResponse(
            inbox_id=inbox.id,
            address=inbox.address,
            token=token,
            created_at=inbox.created_at,
            expires_at=inbox.expires_at,
        )
    
    async def get_inbox(self, inbox_id: UUID) -> Optional[Inbox]:
        """
        Get inbox by ID.
        
        Args:
            inbox_id: Inbox UUID
        
        Returns:
            Inbox: Inbox model or None if not found
        """
        result = await self.db.execute(
            select(Inbox).where(Inbox.id == inbox_id)
        )
        inbox = result.scalar_one_or_none()
        
        if inbox and inbox.expires_at < datetime.utcnow():
            logger.warning(f"Inbox expired: {inbox_id}")
            return None
        
        return inbox
    
    async def get_inbox_by_address(self, address: str) -> Optional[Inbox]:
        """
        Get inbox by email address.
        
        Args:
            address: Email address
        
        Returns:
            Inbox: Inbox model or None if not found
        """
        # Try Redis first
        inbox_id_str = await self.redis.get(f"inbox:{address}")
        
        if inbox_id_str:
            return await self.get_inbox(UUID(inbox_id_str))
        
        # Fallback to database
        result = await self.db.execute(
            select(Inbox).where(Inbox.address == address)
        )
        inbox = result.scalar_one_or_none()
        
        if inbox and inbox.expires_at < datetime.utcnow():
            return None
        
        return inbox
    
    async def delete_inbox(self, inbox_id: UUID) -> bool:
        """
        Delete an inbox and all its messages.
        
        Args:
            inbox_id: Inbox UUID
        
        Returns:
            bool: True if deleted
        
        Raises:
            InboxNotFoundException: If inbox not found
        """
        inbox = await self.get_inbox(inbox_id)
        
        if not inbox:
            raise InboxNotFoundException(str(inbox_id))
        
        # Delete from Redis
        await self.redis.delete(f"inbox:{inbox.address}")
        await self.redis.delete(f"inbox:id:{inbox_id}")
        await self.redis.delete(f"inbox:count:{inbox.address}")
        
        # Delete from database (cascade will delete messages)
        await self.db.delete(inbox)
        await self.db.commit()
        
        logger.info(f"Deleted inbox: {inbox.address}")
        
        return True
    
    async def check_quota(self, inbox_id: UUID) -> bool:
        """
        Check if inbox has capacity for more messages.
        
        Args:
            inbox_id: Inbox UUID
        
        Returns:
            bool: True if within quota
        
        Raises:
            QuotaExceededException: If quota exceeded
        """
        inbox = await self.get_inbox(inbox_id)
        
        if not inbox:
            raise InboxNotFoundException(str(inbox_id))
        
        if inbox.message_count >= settings.MAX_EMAILS_PER_INBOX:
            raise QuotaExceededException(settings.MAX_EMAILS_PER_INBOX)
        
        return True
    
    async def increment_message_count(self, inbox_id: UUID) -> int:
        """
        Increment message count for inbox.
        
        Args:
            inbox_id: Inbox UUID
        
        Returns:
            int: New message count
        """
        inbox = await self.get_inbox(inbox_id)
        
        if not inbox:
            raise InboxNotFoundException(str(inbox_id))
        
        inbox.message_count += 1
        await self.db.commit()
        
        # Update Redis counter
        address = inbox.address
        await self.redis.incr(f"inbox:count:{address}")
        
        return inbox.message_count
    
    async def _address_exists(self, address: str) -> bool:
        """Check if address already exists."""
        result = await self.db.execute(
            select(Inbox).where(Inbox.address == address)
        )
        return result.scalar_one_or_none() is not None
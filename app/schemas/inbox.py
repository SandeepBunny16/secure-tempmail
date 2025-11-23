"""
Inbox-related Pydantic schemas.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr


class InboxCreate(BaseModel):
    """Request schema for creating an inbox."""
    
    ttl_hours: Optional[int] = Field(default=24, ge=1, le=168, description="Inbox TTL in hours (1-168)")


class InboxResponse(BaseModel):
    """Response schema after creating an inbox."""
    
    inbox_id: UUID = Field(..., description="Inbox unique ID")
    address: EmailStr = Field(..., description="Generated email address")
    token: str = Field(..., description="Access token for this inbox")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: datetime = Field(..., description="Expiration timestamp")
    
    class Config:
        from_attributes = True


class InboxDetail(BaseModel):
    """Detailed inbox information."""
    
    inbox_id: UUID = Field(..., description="Inbox unique ID")
    address: EmailStr = Field(..., description="Email address")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: datetime = Field(..., description="Expiration timestamp")
    is_active: bool = Field(..., description="Active status")
    message_count: int = Field(..., description="Number of messages")
    
    class Config:
        from_attributes = True
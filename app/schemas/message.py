"""
Message-related Pydantic schemas.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr


class AttachmentResponse(BaseModel):
    """Attachment response schema."""
    
    id: UUID = Field(..., description="Attachment ID")
    filename: str = Field(..., description="File name")
    content_type: str = Field(..., description="MIME type")
    size_bytes: int = Field(..., description="Size in bytes")
    
    class Config:
        from_attributes = True


class MessageList(BaseModel):
    """Message list item (preview)."""
    
    id: UUID = Field(..., description="Message ID")
    from_address: EmailStr = Field(..., description="Sender email")
    subject: str = Field(..., description="Email subject")
    preview: Optional[str] = Field(None, description="Message preview (first 150 chars)")
    received_at: datetime = Field(..., description="Received timestamp")
    has_attachments: bool = Field(..., description="Has attachments flag")
    is_read: bool = Field(..., description="Read status")
    
    class Config:
        from_attributes = True


class MessageDetail(BaseModel):
    """Complete message details."""
    
    id: UUID = Field(..., description="Message ID")
    from_address: EmailStr = Field(..., description="Sender email")
    to_address: EmailStr = Field(..., description="Recipient email")
    subject: str = Field(..., description="Email subject")
    body_html: Optional[str] = Field(None, description="HTML body (sanitized)")
    body_text: Optional[str] = Field(None, description="Plain text body")
    received_at: datetime = Field(..., description="Received timestamp")
    size_bytes: int = Field(..., description="Total size in bytes")
    has_attachments: bool = Field(..., description="Has attachments flag")
    attachments: List[AttachmentResponse] = Field(default_factory=list, description="Attachments")
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Generic message response wrapper."""
    
    messages: List[MessageList] = Field(..., description="List of messages")
    count: int = Field(..., description="Total message count")
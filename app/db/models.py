"""
SQLAlchemy Database Models

Production-ready models with proper indexes, constraints, and relationships.
"""

import uuid
from datetime import datetime
from typing import List

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    ForeignKey,
    Index,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Inbox(Base):
    """Inbox model for temporary email addresses."""
    
    __tablename__ = "inboxes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    address = Column(String(255), unique=True, nullable=False, index=True)
    token_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    message_count = Column(Integer, default=0, nullable=False)
    metadata = Column(JSONB, default=dict, nullable=False)
    
    messages = relationship("Message", back_populates="inbox", cascade="all, delete-orphan", lazy="select")
    
    __table_args__ = (
        Index("idx_inbox_expires_active", "expires_at", "is_active"),
        Index("idx_inbox_created", "created_at"),
        CheckConstraint("message_count >= 0", name="ck_inbox_message_count_positive"),
    )
    
    def __repr__(self):
        return f"<Inbox(id={self.id}, address={self.address})>"


class Message(Base):
    """Message model for received emails."""
    
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    inbox_id = Column(UUID(as_uuid=True), ForeignKey("inboxes.id", ondelete="CASCADE"), nullable=False, index=True)
    from_address = Column(String(255), nullable=False, index=True)
    to_address = Column(String(255), nullable=False)
    subject = Column(String(998), nullable=False, default="")
    body_html_encrypted = Column(Text, nullable=True)
    body_text_encrypted = Column(Text, nullable=True)
    raw_email_encrypted = Column(Text, nullable=False)
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    size_bytes = Column(Integer, nullable=False)
    has_attachments = Column(Boolean, default=False, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    headers = Column(JSONB, default=dict, nullable=False)
    metadata = Column(JSONB, default=dict, nullable=False)
    
    inbox = relationship("Inbox", back_populates="messages")
    attachments = relationship("Attachment", back_populates="message", cascade="all, delete-orphan", lazy="select")
    
    __table_args__ = (
        Index("idx_message_inbox_received", "inbox_id", "received_at"),
        Index("idx_message_from", "from_address"),
        CheckConstraint("size_bytes > 0", name="ck_message_size_positive"),
    )
    
    def __repr__(self):
        return f"<Message(id={self.id}, from={self.from_address}, subject={self.subject[:30]})>"


class Attachment(Base):
    """Attachment model for email attachments."""
    
    __tablename__ = "attachments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(255), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    content_encrypted = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    message = relationship("Message", back_populates="attachments")
    
    __table_args__ = (
        Index("idx_attachment_message", "message_id"),
        CheckConstraint("size_bytes > 0", name="ck_attachment_size_positive"),
    )
    
    def __repr__(self):
        return f"<Attachment(id={self.id}, filename={self.filename})>"
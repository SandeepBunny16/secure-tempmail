"""
Message Service

Business logic for message management:
- Email reception and storage
- Encryption/decryption
- HTML sanitization
- Attachment handling
"""

import base64
from datetime import datetime
from email.message import Message as EmailMessage
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.config import get_settings
from app.core.exceptions import MessageNotFoundException, InboxNotFoundException
from app.core.logging import get_logger
from app.core.metrics import record_message_received, record_message_deleted
from app.db.models import Message, Attachment, Inbox
from app.schemas.message import MessageList, MessageDetail, AttachmentResponse
from app.services.encryption_service import EncryptionService
from app.services.sanitization_service import SanitizationService

settings = get_settings()
logger = get_logger(__name__)


class MessageService:
    """Service for managing messages."""
    
    def __init__(self, db: AsyncSession, redis, encryption: EncryptionService, sanitization: SanitizationService):
        self.db = db
        self.redis = redis
        self.encryption = encryption
        self.sanitization = sanitization
    
    async def store_message(
        self,
        inbox_id: UUID,
        from_address: str,
        subject: str,
        body_html: Optional[str],
        body_text: Optional[str],
        raw_email: bytes,
        headers: dict,
        attachments: List[dict] = None,
    ) -> Message:
        """
        Store a new email message.
        
        Args:
            inbox_id: Target inbox UUID
            from_address: Sender email address
            subject: Email subject
            body_html: HTML body (will be sanitized and encrypted)
            body_text: Plain text body (will be encrypted)
            raw_email: Raw email bytes (will be encrypted)
            headers: Email headers
            attachments: List of attachments (will be encrypted)
        
        Returns:
            Message: Created message model
        """
        # Encrypt message bodies
        body_html_encrypted = None
        if body_html:
            sanitized_html = self.sanitization.sanitize_html(body_html)
            body_html_encrypted = self.encryption.encrypt(sanitized_html)
        
        body_text_encrypted = None
        if body_text:
            body_text_encrypted = self.encryption.encrypt(body_text)
        
        # Encrypt raw email
        raw_email_str = raw_email.decode('utf-8', errors='replace')
        raw_email_encrypted = self.encryption.encrypt(raw_email_str)
        
        # Calculate size
        size_bytes = len(raw_email)
        
        # Create message
        message = Message(
            inbox_id=inbox_id,
            from_address=from_address[:255],
            to_address="",  # Will be set from inbox
            subject=subject[:998],
            body_html_encrypted=body_html_encrypted,
            body_text_encrypted=body_text_encrypted,
            raw_email_encrypted=raw_email_encrypted,
            size_bytes=size_bytes,
            has_attachments=bool(attachments),
            is_read=False,
            headers=headers,
        )
        
        self.db.add(message)
        await self.db.flush()
        
        # Store attachments
        if attachments:
            for att_data in attachments:
                attachment = Attachment(
                    message_id=message.id,
                    filename=att_data['filename'][:255],
                    content_type=att_data['content_type'][:255],
                    size_bytes=att_data['size'],
                    content_encrypted=self.encryption.encrypt(att_data['content']),
                )
                self.db.add(attachment)
        
        await self.db.commit()
        await self.db.refresh(message)
        
        # Record metrics
        record_message_received(size_bytes)
        
        logger.info(f"Stored message: {message.id} for inbox {inbox_id}")
        
        return message
    
    async def get_messages(self, inbox_id: UUID, limit: int = 50, offset: int = 0) -> List[MessageList]:
        """
        Get messages for an inbox.
        
        Args:
            inbox_id: Inbox UUID
            limit: Maximum number of messages to return
            offset: Offset for pagination
        
        Returns:
            List[MessageList]: List of message previews
        """
        result = await self.db.execute(
            select(Message)
            .where(Message.inbox_id == inbox_id)
            .order_by(desc(Message.received_at))
            .limit(limit)
            .offset(offset)
        )
        
        messages = result.scalars().all()
        
        # Convert to response schema with preview
        message_list = []
        for msg in messages:
            # Decrypt and create preview from text body
            preview = None
            if msg.body_text_encrypted:
                try:
                    full_text = self.encryption.decrypt(msg.body_text_encrypted)
                    preview = full_text[:150] + "..." if len(full_text) > 150 else full_text
                except:
                    preview = "[Unable to decrypt preview]"
            
            message_list.append(MessageList(
                id=msg.id,
                from_address=msg.from_address,
                subject=msg.subject,
                preview=preview,
                received_at=msg.received_at,
                has_attachments=msg.has_attachments,
                is_read=msg.is_read,
            ))
        
        return message_list
    
    async def get_message(self, message_id: UUID) -> MessageDetail:
        """
        Get full message details.
        
        Args:
            message_id: Message UUID
        
        Returns:
            MessageDetail: Complete message with decrypted content
        
        Raises:
            MessageNotFoundException: If message not found
        """
        result = await self.db.execute(
            select(Message)
            .options(joinedload(Message.attachments))
            .where(Message.id == message_id)
        )
        
        message = result.scalar_one_or_none()
        
        if not message:
            raise MessageNotFoundException(str(message_id))
        
        # Decrypt bodies
        body_html = None
        if message.body_html_encrypted:
            body_html = self.encryption.decrypt(message.body_html_encrypted)
        
        body_text = None
        if message.body_text_encrypted:
            body_text = self.encryption.decrypt(message.body_text_encrypted)
        
        # Convert attachments
        attachments = [
            AttachmentResponse(
                id=att.id,
                filename=att.filename,
                content_type=att.content_type,
                size_bytes=att.size_bytes,
            )
            for att in message.attachments
        ]
        
        # Mark as read
        if not message.is_read:
            message.is_read = True
            await self.db.commit()
        
        return MessageDetail(
            id=message.id,
            from_address=message.from_address,
            to_address=message.to_address,
            subject=message.subject,
            body_html=body_html,
            body_text=body_text,
            received_at=message.received_at,
            size_bytes=message.size_bytes,
            has_attachments=message.has_attachments,
            attachments=attachments,
        )
    
    async def delete_message(self, message_id: UUID) -> bool:
        """
        Delete a message.
        
        Args:
            message_id: Message UUID
        
        Returns:
            bool: True if deleted
        
        Raises:
            MessageNotFoundException: If message not found
        """
        result = await self.db.execute(
            select(Message).where(Message.id == message_id)
        )
        
        message = result.scalar_one_or_none()
        
        if not message:
            raise MessageNotFoundException(str(message_id))
        
        await self.db.delete(message)
        await self.db.commit()
        
        # Record metrics
        record_message_deleted()
        
        logger.info(f"Deleted message: {message_id}")
        
        return True
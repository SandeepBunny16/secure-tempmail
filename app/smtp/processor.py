"""
Email Processor

Parses and processes incoming emails:
- Extract headers
- Extract bodies (HTML and text)
- Extract attachments
- Store in database with encryption
"""

import base64
from email.message import Message as EmailMessage
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from app.core.logging import get_logger
from app.services.inbox_service import InboxService
from app.services.message_service import MessageService

logger = get_logger(__name__)


class EmailProcessor:
    """
    Process incoming email messages.
    
    Extracts content, encrypts sensitive data, and stores in database.
    """
    
    def __init__(self, db_factory, redis_client, encryption_service, sanitization_service):
        self.db_factory = db_factory
        self.redis = redis_client
        self.encryption = encryption_service
        self.sanitization = sanitization_service
    
    async def process_message(
        self,
        recipient: str,
        sender: str,
        message: EmailMessage,
        raw_content: bytes,
    ) -> None:
        """
        Process and store an email message.
        
        Args:
            recipient: Recipient email address
            sender: Sender email address
            message: Parsed email message
            raw_content: Raw email bytes
        """
        # Get inbox ID
        inbox_id_str = await self.redis.get(f"inbox:{recipient}")
        if not inbox_id_str:
            raise ValueError(f"Inbox not found: {recipient}")
        
        inbox_id = UUID(inbox_id_str)
        
        # Extract message components
        subject = self._extract_subject(message)
        body_html, body_text = self._extract_bodies(message)
        headers = self._extract_headers(message)
        attachments = self._extract_attachments(message)
        
        # Store message using service
        async with self.db_factory() as db:
            inbox_service = InboxService(db, self.redis, self.encryption)
            message_service = MessageService(db, self.redis, self.encryption, self.sanitization)
            
            # Store message
            await message_service.store_message(
                inbox_id=inbox_id,
                from_address=sender,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                raw_email=raw_content,
                headers=headers,
                attachments=attachments,
            )
            
            # Increment inbox message count
            await inbox_service.increment_message_count(inbox_id)
        
        logger.info(f"Processed email for {recipient} from {sender}")
    
    def _extract_subject(self, message: EmailMessage) -> str:
        """
        Extract email subject.
        
        Args:
            message: Email message
        
        Returns:
            str: Subject line (empty string if not found)
        """
        subject = message.get("Subject", "")
        if isinstance(subject, str):
            return subject
        return str(subject)
    
    def _extract_bodies(self, message: EmailMessage) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract HTML and text bodies from email.
        
        Args:
            message: Email message
        
        Returns:
            tuple: (html_body, text_body)
        """
        html_body = None
        text_body = None
        
        # Walk through message parts
        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type()
                
                if content_type == "text/plain" and not text_body:
                    try:
                        text_body = part.get_content()
                    except:
                        text_body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                
                elif content_type == "text/html" and not html_body:
                    try:
                        html_body = part.get_content()
                    except:
                        html_body = part.get_payload(decode=True).decode('utf-8', errors='replace')
        else:
            # Single part message
            content_type = message.get_content_type()
            if content_type == "text/plain":
                try:
                    text_body = message.get_content()
                except:
                    text_body = message.get_payload(decode=True).decode('utf-8', errors='replace')
            elif content_type == "text/html":
                try:
                    html_body = message.get_content()
                except:
                    html_body = message.get_payload(decode=True).decode('utf-8', errors='replace')
        
        return html_body, text_body
    
    def _extract_headers(self, message: EmailMessage) -> Dict[str, str]:
        """
        Extract email headers.
        
        Args:
            message: Email message
        
        Returns:
            dict: Header name-value pairs
        """
        headers = {}
        
        # Extract common headers
        common_headers = [
            "From", "To", "Cc", "Bcc", "Subject", "Date",
            "Message-ID", "In-Reply-To", "References",
            "Return-Path", "Reply-To",
        ]
        
        for header_name in common_headers:
            value = message.get(header_name)
            if value:
                headers[header_name] = str(value)
        
        return headers
    
    def _extract_attachments(self, message: EmailMessage) -> List[Dict[str, any]]:
        """
        Extract email attachments.
        
        Args:
            message: Email message
        
        Returns:
            list: List of attachment dictionaries
        """
        attachments = []
        
        if not message.is_multipart():
            return attachments
        
        for part in message.walk():
            # Skip non-attachment parts
            if part.get_content_maintype() == "multipart":
                continue
            if part.get("Content-Disposition") is None:
                continue
            
            filename = part.get_filename()
            if not filename:
                continue
            
            try:
                # Get attachment content
                content = part.get_payload(decode=True)
                
                if content:
                    # Encode as base64 string for storage
                    content_b64 = base64.b64encode(content).decode('utf-8')
                    
                    attachments.append({
                        "filename": filename,
                        "content_type": part.get_content_type(),
                        "size": len(content),
                        "content": content_b64,
                    })
            except Exception as e:
                logger.warning(f"Failed to extract attachment {filename}: {str(e)}")
                continue
        
        return attachments
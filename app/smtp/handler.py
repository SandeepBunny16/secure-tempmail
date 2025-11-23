"""
SMTP Handler

Handles incoming SMTP connections and email reception.
"""

import time
from email import policy
from email.parser import BytesParser
from typing import Optional

from aiosmtpd.smtp import Envelope, Session, SMTP as SMTPProtocol

from app.config import get_settings
from app.core.logging import get_logger
from app.core.metrics import record_smtp_connection, record_smtp_message, record_smtp_rejection
from app.smtp.processor import EmailProcessor

settings = get_settings()
logger = get_logger(__name__)


class TempMailHandler:
    """
    SMTP handler for receiving emails to temporary addresses.
    
    Implements security checks, validation, and message processing.
    """
    
    def __init__(self, db_factory, redis_client, encryption_service, sanitization_service):
        self.db_factory = db_factory
        self.redis = redis_client
        self.encryption = encryption_service
        self.sanitization = sanitization_service
        self.processor = EmailProcessor(
            db_factory=db_factory,
            redis_client=redis_client,
            encryption_service=encryption_service,
            sanitization_service=sanitization_service,
        )
    
    async def handle_DATA(self, server: SMTPProtocol, session: Session, envelope: Envelope) -> str:
        """
        Handle incoming email data.
        
        Args:
            server: SMTP server instance
            session: SMTP session
            envelope: Email envelope with recipients and data
        
        Returns:
            str: SMTP response code and message
        """
        start_time = time.time()
        
        try:
            # Record connection
            record_smtp_connection()
            
            # Validate envelope
            if not envelope.rcpt_tos:
                logger.warning("Email rejected: No recipients")
                record_smtp_rejection("no_recipients")
                return "554 No valid recipients"
            
            # Get recipient address (we only support single recipient)
            recipient = envelope.rcpt_tos[0].lower()
            
            # Validate recipient exists and is not expired
            if not await self._validate_recipient(recipient):
                logger.warning(f"Email rejected: Invalid recipient {recipient}")
                record_smtp_rejection("invalid_recipient")
                return "550 Recipient not found or expired"
            
            # Check inbox quota
            if not await self._check_inbox_quota(recipient):
                logger.warning(f"Email rejected: Quota exceeded for {recipient}")
                record_smtp_rejection("quota_exceeded")
                return "552 Inbox quota exceeded"
            
            # Validate message size
            message_size = len(envelope.content)
            if message_size > self._max_message_size():
                logger.warning(f"Email rejected: Message too large ({message_size} bytes)")
                record_smtp_rejection("too_large")
                return "552 Message size exceeds maximum"
            
            # Parse email message
            try:
                parser = BytesParser(policy=policy.default)
                message = parser.parsebytes(envelope.content)
            except Exception as e:
                logger.error(f"Email parsing failed: {str(e)}")
                record_smtp_rejection("parse_error")
                return "451 Error parsing message"
            
            # Process and store message
            try:
                await self.processor.process_message(
                    recipient=recipient,
                    sender=envelope.mail_from,
                    message=message,
                    raw_content=envelope.content,
                )
            except Exception as e:
                logger.error(f"Message processing failed: {str(e)}", exc_info=True)
                record_smtp_message("error", time.time() - start_time)
                return "451 Requested action aborted: error in processing"
            
            # Success
            duration = time.time() - start_time
            record_smtp_message("accepted", duration)
            logger.info(f"Email accepted for {recipient} ({message_size} bytes, {duration:.2f}s)")
            return "250 Message accepted for delivery"
            
        except Exception as e:
            logger.error(f"Unexpected error in SMTP handler: {str(e)}", exc_info=True)
            record_smtp_message("error", time.time() - start_time)
            return "451 Temporary server error"
    
    async def _validate_recipient(self, recipient: str) -> bool:
        """
        Check if recipient inbox exists and is not expired.
        
        Args:
            recipient: Email address
        
        Returns:
            bool: True if valid
        """
        try:
            inbox_id = await self.redis.get(f"inbox:{recipient}")
            return inbox_id is not None
        except Exception as e:
            logger.error(f"Redis error checking recipient: {str(e)}")
            return False
    
    async def _check_inbox_quota(self, recipient: str) -> bool:
        """
        Check if inbox has capacity for more messages.
        
        Args:
            recipient: Email address
        
        Returns:
            bool: True if within quota
        """
        try:
            count = await self.redis.get(f"inbox:count:{recipient}")
            if count is None:
                return True
            return int(count) < self._max_emails_per_inbox()
        except Exception as e:
            logger.error(f"Redis error checking quota: {str(e)}")
            return True  # Allow on error
    
    def _max_message_size(self) -> int:
        """Get maximum message size from config."""
        return settings.max_email_size_bytes
    
    def _max_emails_per_inbox(self) -> int:
        """Get maximum emails per inbox from config."""
        return settings.MAX_EMAILS_PER_INBOX
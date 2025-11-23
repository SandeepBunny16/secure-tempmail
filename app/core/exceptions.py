"""
Custom Exceptions

Application-specific exceptions with proper error codes and messages.
"""

from typing import Optional, Any


class TempMailException(Exception):
    """
    Base exception for all TempMail errors.
    """
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "internal_error",
        detail: Optional[Any] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.detail = detail
        super().__init__(self.message)


class InboxNotFoundException(TempMailException):
    """
    Raised when inbox is not found.
    """
    
    def __init__(self, inbox_id: str, detail: Optional[Any] = None):
        super().__init__(
            message=f"Inbox not found: {inbox_id}",
            status_code=404,
            error_code="inbox_not_found",
            detail=detail,
        )


class InboxExpiredException(TempMailException):
    """
    Raised when inbox has expired.
    """
    
    def __init__(self, inbox_id: str, detail: Optional[Any] = None):
        super().__init__(
            message=f"Inbox has expired: {inbox_id}",
            status_code=410,
            error_code="inbox_expired",
            detail=detail,
        )


class MessageNotFoundException(TempMailException):
    """
    Raised when message is not found.
    """
    
    def __init__(self, message_id: str, detail: Optional[Any] = None):
        super().__init__(
            message=f"Message not found: {message_id}",
            status_code=404,
            error_code="message_not_found",
            detail=detail,
        )


class QuotaExceededException(TempMailException):
    """
    Raised when inbox quota is exceeded.
    """
    
    def __init__(self, limit: int, detail: Optional[Any] = None):
        super().__init__(
            message=f"Inbox quota exceeded. Maximum {limit} emails allowed.",
            status_code=429,
            error_code="quota_exceeded",
            detail=detail,
        )


class InvalidTokenException(TempMailException):
    """
    Raised when authentication token is invalid.
    """
    
    def __init__(self, detail: Optional[Any] = None):
        super().__init__(
            message="Invalid or expired authentication token",
            status_code=401,
            error_code="invalid_token",
            detail=detail,
        )


class RateLimitExceededException(TempMailException):
    """
    Raised when rate limit is exceeded.
    """
    
    def __init__(self, retry_after: int = 60, detail: Optional[Any] = None):
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            status_code=429,
            error_code="rate_limit_exceeded",
            detail={"retry_after": retry_after, **(detail or {})},
        )


class ValidationException(TempMailException):
    """
    Raised when input validation fails.
    """
    
    def __init__(self, field: str, message: str, detail: Optional[Any] = None):
        super().__init__(
            message=f"Validation failed for {field}: {message}",
            status_code=422,
            error_code="validation_error",
            detail=detail,
        )


class EncryptionException(TempMailException):
    """
    Raised when encryption/decryption fails.
    """
    
    def __init__(self, message: str = "Encryption operation failed", detail: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="encryption_error",
            detail=detail,
        )


class SanitizationException(TempMailException):
    """
    Raised when HTML sanitization fails.
    """
    
    def __init__(self, message: str = "HTML sanitization failed", detail: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="sanitization_error",
            detail=detail,
        )


class EmailProcessingException(TempMailException):
    """
    Raised when email processing fails.
    """
    
    def __init__(self, message: str = "Email processing failed", detail: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="email_processing_error",
            detail=detail,
        )


class DatabaseException(TempMailException):
    """
    Raised when database operation fails.
    """
    
    def __init__(self, message: str = "Database operation failed", detail: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="database_error",
            detail=detail,
        )


class RedisException(TempMailException):
    """
    Raised when Redis operation fails.
    """
    
    def __init__(self, message: str = "Redis operation failed", detail: Optional[Any] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="redis_error",
            detail=detail,
        )
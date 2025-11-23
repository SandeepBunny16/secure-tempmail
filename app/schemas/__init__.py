"""
Pydantic Schemas

Request and response models for API validation.
"""

from app.schemas.inbox import (
    InboxCreate,
    InboxResponse,
    InboxDetail,
)
from app.schemas.message import (
    MessageList,
    MessageDetail,
    MessageResponse,
    AttachmentResponse,
)
from app.schemas.common import (
    HealthResponse,
    ErrorResponse,
)

__all__ = [
    "InboxCreate",
    "InboxResponse",
    "InboxDetail",
    "MessageList",
    "MessageDetail",
    "MessageResponse",
    "AttachmentResponse",
    "HealthResponse",
    "ErrorResponse",
]
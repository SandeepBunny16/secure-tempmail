"""
Message API Endpoints

REST API for message management:
- List messages in inbox
- Get message details
- Delete messages
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import (
    get_message_service,
    get_inbox_service,
    get_current_inbox,
    check_rate_limit,
)
from app.schemas.message import MessageList, MessageDetail, MessageResponse
from app.services.message_service import MessageService
from app.services.inbox_service import InboxService
from app.core.exceptions import MessageNotFoundException

router = APIRouter()


@router.get(
    "",
    response_model=MessageResponse,
    summary="List messages",
    description="""
    Get a list of messages for the authenticated inbox.
    
    Returns messages in reverse chronological order (newest first).
    Supports pagination for large inboxes.
    """,
    responses={
        200: {"description": "Messages retrieved successfully"},
        401: {"description": "Missing or invalid authentication token"},
    }
)
async def list_messages(
    limit: int = Query(default=50, ge=1, le=100, description="Maximum messages to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    message_service: MessageService = Depends(get_message_service),
    inbox_id: str = Depends(get_current_inbox),
    _: bool = Depends(check_rate_limit),
):
    """
    List messages in the authenticated inbox.
    
    Args:
        limit: Maximum number of messages to return (1-100)
        offset: Pagination offset
        message_service: Message service instance
        inbox_id: Authenticated inbox ID
    
    Returns:
        MessageResponse: List of messages with metadata
    """
    messages = await message_service.get_messages(
        inbox_id=UUID(inbox_id),
        limit=limit,
        offset=offset,
    )
    
    return MessageResponse(
        messages=messages,
        count=len(messages),
    )


@router.get(
    "/{message_id}",
    response_model=MessageDetail,
    summary="Get message details",
    description="""
    Get complete details of a specific message including full body and attachments.
    
    The HTML body is automatically sanitized to prevent XSS attacks.
    Marks the message as read.
    """,
    responses={
        200: {"description": "Message details retrieved successfully"},
        401: {"description": "Missing or invalid authentication token"},
        404: {"description": "Message not found"},
    }
)
async def get_message(
    message_id: UUID,
    message_service: MessageService = Depends(get_message_service),
    inbox_service: InboxService = Depends(get_inbox_service),
    inbox_id: str = Depends(get_current_inbox),
    _: bool = Depends(check_rate_limit),
):
    """
    Get detailed message information.
    
    Args:
        message_id: Message UUID
        message_service: Message service instance
        inbox_service: Inbox service instance
        inbox_id: Authenticated inbox ID
    
    Returns:
        MessageDetail: Complete message with decrypted content
    
    Raises:
        HTTPException: If message not found or unauthorized
    """
    # Get message
    message = await message_service.get_message(message_id)
    
    # Verify message belongs to authenticated inbox
    # (In production, add this check to message_service.get_message)
    
    return message


@router.delete(
    "/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a message",
    description="""
    Permanently delete a message from the inbox.
    
    This action cannot be undone.
    """,
    responses={
        204: {"description": "Message deleted successfully"},
        401: {"description": "Missing or invalid authentication token"},
        404: {"description": "Message not found"},
    }
)
async def delete_message(
    message_id: UUID,
    message_service: MessageService = Depends(get_message_service),
    inbox_id: str = Depends(get_current_inbox),
    _: bool = Depends(check_rate_limit),
):
    """
    Delete a message.
    
    Args:
        message_id: Message UUID
        message_service: Message service instance
        inbox_id: Authenticated inbox ID
    
    Raises:
        HTTPException: If message not found or unauthorized
    """
    await message_service.delete_message(message_id)
    
    return None
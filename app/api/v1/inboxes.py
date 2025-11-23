"""
Inbox API Endpoints

REST API for inbox management:
- Create temporary inbox
- Get inbox details
- Delete inbox
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import (
    get_inbox_service,
    get_current_inbox,
    check_rate_limit,
    check_inbox_creation_limit,
)
from app.schemas.inbox import InboxCreate, InboxResponse, InboxDetail
from app.services.inbox_service import InboxService
from app.core.exceptions import InboxNotFoundException

router = APIRouter()


@router.post(
    "",
    response_model=InboxResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new temporary inbox",
    description="""
    Create a new temporary email inbox with a randomly generated address.
    
    The inbox will automatically expire after the specified TTL (default: 24 hours).
    Returns an access token that must be used for all subsequent requests.
    
    **Rate Limits:**
    - 10 inbox creations per hour per IP address
    - 60 requests per minute per IP address
    """,
    responses={
        201: {
            "description": "Inbox created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "inbox_id": "123e4567-e89b-12d3-a456-426614174000",
                        "address": "tmp_abc123xyz456@tempmail.local",
                        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "created_at": "2024-01-15T10:30:00Z",
                        "expires_at": "2024-01-16T10:30:00Z"
                    }
                }
            }
        },
        429: {"description": "Rate limit exceeded"},
    }
)
async def create_inbox(
    request: Request,
    inbox_create: InboxCreate = InboxCreate(),
    inbox_service: InboxService = Depends(get_inbox_service),
    _: bool = Depends(check_rate_limit),
    __: bool = Depends(check_inbox_creation_limit),
):
    """
    Create a new temporary inbox.
    
    Args:
        inbox_create: Inbox creation parameters (ttl_hours)
        inbox_service: Inbox service instance
    
    Returns:
        InboxResponse: Created inbox with token
    """
    return await inbox_service.create_inbox(ttl_hours=inbox_create.ttl_hours)


@router.get(
    "/{inbox_id}",
    response_model=InboxDetail,
    summary="Get inbox details",
    description="""
    Get detailed information about a specific inbox.
    
    Requires authentication with the inbox access token.
    """,
    responses={
        200: {"description": "Inbox details retrieved successfully"},
        401: {"description": "Missing or invalid authentication token"},
        404: {"description": "Inbox not found or expired"},
    }
)
async def get_inbox(
    inbox_id: UUID,
    inbox_service: InboxService = Depends(get_inbox_service),
    authenticated_inbox_id: str = Depends(get_current_inbox),
):
    """
    Get inbox details by ID.
    
    Args:
        inbox_id: Inbox UUID
        inbox_service: Inbox service instance
        authenticated_inbox_id: Authenticated inbox ID from token
    
    Returns:
        InboxDetail: Inbox information
    
    Raises:
        HTTPException: If inbox not found or unauthorized
    """
    # Verify user has access to this inbox
    if str(inbox_id) != authenticated_inbox_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this inbox"
        )
    
    inbox = await inbox_service.get_inbox(inbox_id)
    
    if not inbox:
        raise InboxNotFoundException(str(inbox_id))
    
    return InboxDetail(
        inbox_id=inbox.id,
        address=inbox.address,
        created_at=inbox.created_at,
        expires_at=inbox.expires_at,
        is_active=inbox.is_active,
        message_count=inbox.message_count,
    )


@router.delete(
    "/{inbox_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an inbox",
    description="""
    Permanently delete an inbox and all its messages.
    
    This action cannot be undone. All emails in the inbox will be permanently deleted.
    """,
    responses={
        204: {"description": "Inbox deleted successfully"},
        401: {"description": "Missing or invalid authentication token"},
        403: {"description": "Not authorized to delete this inbox"},
        404: {"description": "Inbox not found"},
    }
)
async def delete_inbox(
    inbox_id: UUID,
    inbox_service: InboxService = Depends(get_inbox_service),
    authenticated_inbox_id: str = Depends(get_current_inbox),
):
    """
    Delete an inbox and all its messages.
    
    Args:
        inbox_id: Inbox UUID
        inbox_service: Inbox service instance
        authenticated_inbox_id: Authenticated inbox ID from token
    
    Raises:
        HTTPException: If inbox not found or unauthorized
    """
    # Verify user has access to this inbox
    if str(inbox_id) != authenticated_inbox_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this inbox"
        )
    
    await inbox_service.delete_inbox(inbox_id)
    
    return None
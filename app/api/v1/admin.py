"""
Admin API Endpoints

Privileged endpoints for system administration:
- System statistics
- Cleanup operations
- Configuration management

Requires API key authentication.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select, func

from app.dependencies import verify_api_key, get_database, get_redis
from app.db.models import Inbox, Message
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/stats",
    summary="Get system statistics",
    description="""
    Get comprehensive system statistics including:
    - Total inboxes
    - Active inboxes
    - Total messages
    - Storage usage
    
    Requires API key authentication.
    """,
    responses={
        200: {"description": "Statistics retrieved successfully"},
        401: {"description": "Missing or invalid API key"},
    },
    dependencies=[Depends(verify_api_key)]
)
async def get_system_stats(
    db = Depends(get_database),
    redis = Depends(get_redis),
):
    """
    Get system statistics.
    
    Args:
        db: Database session
        redis: Redis client
    
    Returns:
        dict: System statistics
    """
    # Count total inboxes
    result = await db.execute(select(func.count()).select_from(Inbox))
    total_inboxes = result.scalar()
    
    # Count active inboxes
    result = await db.execute(
        select(func.count()).select_from(Inbox).where(Inbox.is_active == True)
    )
    active_inboxes = result.scalar()
    
    # Count total messages
    result = await db.execute(select(func.count()).select_from(Message))
    total_messages = result.scalar()
    
    # Get Redis info
    redis_info = await redis.info()
    redis_memory = redis_info.get('used_memory_human', 'Unknown')
    
    return {
        "inboxes": {
            "total": total_inboxes,
            "active": active_inboxes,
            "expired": total_inboxes - active_inboxes,
        },
        "messages": {
            "total": total_messages,
        },
        "storage": {
            "redis_memory": redis_memory,
        }
    }


@router.post(
    "/cleanup",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger manual cleanup",
    description="""
    Manually trigger TTL cleanup of expired inboxes and messages.
    
    This is normally done automatically by the background worker,
    but can be triggered manually for immediate cleanup.
    
    Requires API key authentication.
    """,
    responses={
        202: {"description": "Cleanup triggered successfully"},
        401: {"description": "Missing or invalid API key"},
    },
    dependencies=[Depends(verify_api_key)]
)
async def trigger_cleanup(
    db = Depends(get_database),
):
    """
    Trigger manual cleanup operation.
    
    Args:
        db: Database session
    
    Returns:
        dict: Cleanup result
    """
    from datetime import datetime
    from app.core.metrics import record_inbox_expired
    
    # Delete expired inboxes
    result = await db.execute(
        select(Inbox).where(Inbox.expires_at < datetime.utcnow())
    )
    expired_inboxes = result.scalars().all()
    
    for inbox in expired_inboxes:
        await db.delete(inbox)
        record_inbox_expired()
    
    await db.commit()
    
    logger.info(f"Manual cleanup removed {len(expired_inboxes)} expired inboxes")
    
    return {
        "status": "cleanup_triggered",
        "inboxes_deleted": len(expired_inboxes),
    }
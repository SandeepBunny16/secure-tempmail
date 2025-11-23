"""
TTL Cleanup Worker

Background worker that periodically cleans up expired inboxes and messages.

Run with:
    python -m app.workers.ttl_cleanup
"""

import asyncio
import sys
from datetime import datetime

from sqlalchemy import select, delete

from app.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.metrics import (
    worker_cleanup_runs_total,
    worker_cleanup_duration,
    worker_inboxes_cleaned,
    worker_messages_cleaned,
    worker_errors_total,
    record_inbox_expired,
)
from app.db.session import AsyncSessionLocal
from app.db.redis_client import get_redis_client
from app.db.models import Inbox, Message

settings = get_settings()
setup_logging()
logger = get_logger(__name__)


class TTLCleanupWorker:
    """
    Background worker for cleaning up expired inboxes.
    
    Runs periodically to:
    - Delete expired inboxes and their messages
    - Clean up orphaned Redis keys
    - Update metrics
    """
    
    def __init__(self):
        self.interval = settings.CLEANUP_INTERVAL_MINUTES * 60  # Convert to seconds
        self.batch_size = settings.CLEANUP_BATCH_SIZE
        self.running = False
    
    async def start(self):
        """
        Start the cleanup worker.
        
        Runs indefinitely until stopped or error occurs.
        """
        logger.info("Starting TTL cleanup worker...")
        logger.info(f"Cleanup interval: {settings.CLEANUP_INTERVAL_MINUTES} minutes")
        logger.info(f"Batch size: {self.batch_size}")
        
        self.running = True
        
        # Initialize Redis
        try:
            redis = await get_redis_client()
            await redis.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            sys.exit(1)
        
        # Main cleanup loop
        while self.running:
            try:
                await self._run_cleanup(redis)
                
                # Wait for next interval
                logger.info(f"Waiting {settings.CLEANUP_INTERVAL_MINUTES} minutes until next cleanup...")
                await asyncio.sleep(self.interval)
                
            except asyncio.CancelledError:
                logger.info("Worker cancelled")
                break
            except Exception as e:
                logger.error(f"Cleanup error: {str(e)}", exc_info=True)
                worker_errors_total.labels(worker="ttl_cleanup").inc()
                
                # Wait before retrying
                await asyncio.sleep(60)
        
        # Cleanup
        await redis.close()
        logger.info("TTL cleanup worker stopped")
    
    async def _run_cleanup(self, redis):
        """
        Run a single cleanup cycle.
        
        Args:
            redis: Redis client
        """
        import time
        start_time = time.time()
        
        logger.info("Starting cleanup cycle...")
        worker_cleanup_runs_total.inc()
        
        inboxes_deleted = 0
        messages_deleted = 0
        redis_keys_deleted = 0
        
        try:
            async with AsyncSessionLocal() as db:
                # Find expired inboxes
                now = datetime.utcnow()
                result = await db.execute(
                    select(Inbox)
                    .where(Inbox.expires_at < now)
                    .limit(self.batch_size)
                )
                expired_inboxes = result.scalars().all()
                
                logger.info(f"Found {len(expired_inboxes)} expired inboxes")
                
                for inbox in expired_inboxes:
                    try:
                        # Count messages before deletion (for metrics)
                        result = await db.execute(
                            select(Message).where(Message.inbox_id == inbox.id)
                        )
                        messages = result.scalars().all()
                        msg_count = len(messages)
                        
                        # Delete Redis keys
                        try:
                            await redis.delete(f"inbox:{inbox.address}")
                            await redis.delete(f"inbox:id:{inbox.id}")
                            await redis.delete(f"inbox:count:{inbox.address}")
                            redis_keys_deleted += 3
                        except Exception as e:
                            logger.warning(f"Failed to delete Redis keys for {inbox.address}: {str(e)}")
                        
                        # Delete inbox (cascade will delete messages)
                        await db.delete(inbox)
                        
                        # Update counters
                        inboxes_deleted += 1
                        messages_deleted += msg_count
                        
                        # Update metrics
                        record_inbox_expired()
                        worker_inboxes_cleaned.inc()
                        worker_messages_cleaned.inc(msg_count)
                        
                        logger.debug(f"Deleted expired inbox: {inbox.address} ({msg_count} messages)")
                        
                    except Exception as e:
                        logger.error(f"Failed to delete inbox {inbox.id}: {str(e)}")
                        continue
                
                # Commit all deletions
                await db.commit()
        
        except Exception as e:
            logger.error(f"Database cleanup failed: {str(e)}", exc_info=True)
            raise
        
        # Record duration
        duration = time.time() - start_time
        worker_cleanup_duration.observe(duration)
        
        logger.info(
            f"Cleanup cycle complete: "
            f"{inboxes_deleted} inboxes, "
            f"{messages_deleted} messages, "
            f"{redis_keys_deleted} Redis keys "
            f"({duration:.2f}s)"
        )
    
    async def stop(self):
        """Stop the cleanup worker."""
        logger.info("Stopping cleanup worker...")
        self.running = False


async def run_cleanup_worker():
    """
    Run the TTL cleanup worker.
    
    Entry point for running as a standalone process.
    """
    worker = TTLCleanupWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
        await worker.stop()
    except Exception as e:
        logger.error(f"Worker crashed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(run_cleanup_worker())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker crashed: {str(e)}", exc_info=True)
        sys.exit(1)
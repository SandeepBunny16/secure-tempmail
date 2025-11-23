"""
SMTP Server

Production-ready SMTP server using aiosmtpd.

Run with:
    python -m app.smtp.server
"""

import asyncio
import sys
from aiosmtpd.controller import Controller

from app.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.db.session import AsyncSessionLocal
from app.db.redis_client import get_redis_client
from app.smtp.handler import TempMailHandler
from app.core.security import EncryptionService
from app.services.sanitization_service import SanitizationService

settings = get_settings()
setup_logging()
logger = get_logger(__name__)


async def start_smtp_server():
    """
    Start the SMTP server.
    
    Initializes:
    - Database connection pool
    - Redis connection
    - SMTP handler
    - SMTP controller
    """
    logger.info("Starting SecureTempMail SMTP server...")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"SMTP Host: {settings.SMTP_HOST}:{settings.SMTP_PORT}")
    logger.info(f"Hostname: {settings.SMTP_HOSTNAME}")
    
    try:
        # Initialize Redis
        redis = await get_redis_client()
        await redis.ping()
        logger.info("Redis connection established")
        
        # Initialize services
        encryption_service = EncryptionService()
        sanitization_service = SanitizationService()
        logger.info("Services initialized")
        
        # Create SMTP handler
        handler = TempMailHandler(
            db_factory=AsyncSessionLocal,
            redis_client=redis,
            encryption_service=encryption_service,
            sanitization_service=sanitization_service,
        )
        
        # Create SMTP controller
        controller = Controller(
            handler,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            server_hostname=settings.SMTP_HOSTNAME,
            require_starttls=False,  # We handle TLS at network layer
            enable_SMTPUTF8=True,  # Support international email addresses
        )
        
        # Start controller
        controller.start()
        logger.info(f"SMTP server started on {settings.SMTP_HOST}:{settings.SMTP_PORT}")
        logger.info("Ready to receive emails")
        
        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutting down SMTP server...")
        finally:
            controller.stop()
            await redis.close()
            logger.info("SMTP server stopped")
            
    except Exception as e:
        logger.error(f"SMTP server failed to start: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(start_smtp_server())
    except KeyboardInterrupt:
        logger.info("SMTP server stopped by user")
    except Exception as e:
        logger.error(f"SMTP server crashed: {str(e)}", exc_info=True)
        sys.exit(1)
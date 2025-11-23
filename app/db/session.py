"""
Database Session Management

Provides:
- Async SQLAlchemy engine
- Session factory
- Database connection lifecycle
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from app.config import get_settings
from app.db.base import Base


settings = get_settings()
logger = logging.getLogger(__name__)

# Create async engine
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before using
    poolclass=QueuePool if settings.is_production else NullPool,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database sessions.
    
    Yields:
        AsyncSession: SQLAlchemy async session
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """
    Create all database tables.
    
    Should be called on application startup.
    """
    logger.info("Creating database tables...")
    
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they're registered
            from app.db import models  # noqa: F401
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}", exc_info=True)
        raise


async def drop_tables():
    """
    Drop all database tables.
    
    WARNING: This will delete all data!
    Should only be used in development/testing.
    """
    if settings.is_production:
        raise RuntimeError("Cannot drop tables in production!")
    
    logger.warning("Dropping all database tables...")
    
    async with engine.begin() as conn:
        # Import all models
        from app.db import models  # noqa: F401
        
        # Drop all tables
        await conn.run_sync(Base.metadata.drop_all)
    
    logger.warning("All database tables dropped")
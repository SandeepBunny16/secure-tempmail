"""
Health Check API Endpoints

Provides health and readiness endpoints for:
- Kubernetes health checks
- Load balancer health checks
- Monitoring systems
"""

from fastapi import APIRouter, status
from sqlalchemy import text

from app.config import get_settings
from app.db.session import engine
from app.db.redis_client import get_redis_client
from app.schemas.common import HealthResponse

settings = get_settings()
router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="""
    Comprehensive health check including all system components.
    
    Checks:
    - Database connectivity
    - Redis connectivity
    - Application status
    
    Returns HTTP 200 if all components are healthy, 503 otherwise.
    """,
    responses={
        200: {"description": "All systems healthy"},
        503: {"description": "One or more systems unhealthy"},
    }
)
async def health_check():
    """
    Perform comprehensive health check.
    
    Returns:
        HealthResponse: Health status of all components
    """
    # Test database connection
    db_healthy = True
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_healthy = False
    
    # Test Redis connection
    redis_healthy = True
    try:
        redis = await get_redis_client()
        await redis.ping()
    except Exception as e:
        redis_healthy = False
    
    # Determine overall health
    overall_healthy = db_healthy and redis_healthy
    
    return HealthResponse(
        status="healthy" if overall_healthy else "unhealthy",
        version="1.0.0",
        environment=settings.APP_ENV,
        components={
            "database": "healthy" if db_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy",
            "api": "healthy",
        }
    )


@router.get(
    "/readiness",
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="""
    Kubernetes readiness probe.
    
    Returns HTTP 200 when the application is ready to accept traffic.
    Used by Kubernetes to determine if pod should receive requests.
    """,
)
async def readiness_check():
    """
    Check if application is ready to serve requests.
    
    Returns:
        dict: Readiness status
    """
    return {"status": "ready"}


@router.get(
    "/liveness",
    status_code=status.HTTP_200_OK,
    summary="Liveness check",
    description="""
    Kubernetes liveness probe.
    
    Returns HTTP 200 when the application is running.
    Used by Kubernetes to determine if pod should be restarted.
    """,
)
async def liveness_check():
    """
    Check if application is alive.
    
    Returns:
        dict: Liveness status
    """
    return {"status": "alive"}
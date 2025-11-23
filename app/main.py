"""
FastAPI Application Entry Point

Production-ready FastAPI application with:
- CORS middleware
- Rate limiting
- Security headers
- Error handling
- Metrics collection
- Structured logging
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.config import get_settings
from app.core.exceptions import (
    TempMailException,
    InboxNotFoundException,
    InboxExpiredException,
    QuotaExceededException,
    InvalidTokenException,
)
from app.core.logging import setup_logging, get_logger
from app.core.metrics import (
    requests_total,
    requests_duration,
    active_requests,
)
from app.db.session import engine, create_tables
from app.db.redis_client import get_redis_client

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan handler.
    
    Manages startup and shutdown events:
    - Database table creation
    - Redis connection
    - Resource cleanup
    """
    # Startup
    logger.info("Starting SecureTempMail application")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Domain: {settings.APP_DOMAIN}")
    
    try:
        # Create database tables
        logger.info("Creating database tables...")
        await create_tables()
        logger.info("Database tables created successfully")
        
        # Test Redis connection
        redis = await get_redis_client()
        await redis.ping()
        logger.info("Redis connection established")
        
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}", exc_info=True)
        sys.exit(1)
    
    yield
    
    # Shutdown
    logger.info("Shutting down SecureTempMail application")
    
    try:
        # Close database connections
        await engine.dispose()
        logger.info("Database connections closed")
        
        # Close Redis connection
        redis = await get_redis_client()
        await redis.close()
        logger.info("Redis connection closed")
        
    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}", exc_info=True)


# Create FastAPI application
app = FastAPI(
    title="SecureTempMail API",
    description="Production-ready temporary email system with end-to-end encryption",
    version="1.0.0",
    docs_url="/docs" if settings.APP_ENV == "development" else None,
    redoc_url="/redoc" if settings.APP_ENV == "development" else None,
    lifespan=lifespan,
)


# ===================================
# Middleware Configuration
# ===================================

# CORS Middleware
if settings.ENABLE_CORS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    logger.info(f"CORS enabled for origins: {settings.CORS_ORIGINS}")

# GZip Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Trusted Host Middleware (production)
if settings.APP_ENV == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[settings.APP_DOMAIN, f"*.{settings.APP_DOMAIN}"],
    )


# ===================================
# Request/Response Middleware
# ===================================

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Add security headers to all responses.
    
    Headers:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000
    - Content-Security-Policy: default-src 'self'
    """
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    if settings.APP_ENV == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    if settings.CSP_ENABLED:
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
    
    return response


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """
    Collect Prometheus metrics for all requests.
    
    Metrics:
    - requests_total: Total number of requests
    - requests_duration: Request duration histogram
    - active_requests: Number of active requests
    """
    import time
    
    method = request.method
    path = request.url.path
    
    # Increment active requests
    active_requests.inc()
    
    start_time = time.time()
    
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        status_code = 500
        raise
    finally:
        # Record metrics
        duration = time.time() - start_time
        
        requests_total.labels(
            method=method,
            endpoint=path,
            status=status_code
        ).inc()
        
        requests_duration.labels(
            method=method,
            endpoint=path
        ).observe(duration)
        
        active_requests.dec()
    
    return response


# ===================================
# Exception Handlers
# ===================================

@app.exception_handler(TempMailException)
async def tempmail_exception_handler(request: Request, exc: TempMailException):
    """
    Handle custom TempMail exceptions.
    """
    logger.warning(
        f"TempMail exception: {exc.message}",
        extra={
            "error_code": exc.error_code,
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "detail": exc.detail,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handle HTTP exceptions.
    """
    logger.warning(
        f"HTTP exception: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle request validation errors.
    """
    logger.warning(
        "Request validation failed",
        extra={
            "errors": exc.errors(),
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Invalid request data",
            "detail": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions.
    """
    logger.error(
        f"Unexpected exception: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    # Don't expose internal errors in production
    if settings.APP_ENV == "production":
        message = "Internal server error"
    else:
        message = str(exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "message": message,
        },
    )


# ===================================
# Routes
# ===================================

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

# Mount Prometheus metrics
if settings.ENABLE_METRICS:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    logger.info("Prometheus metrics enabled at /metrics")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    """
    Serve the web UI homepage.
    """
    try:
        with open("app/static/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head><title>SecureTempMail</title></head>
            <body>
                <h1>SecureTempMail API</h1>
                <p>API is running. Visit <a href="/docs">/docs</a> for API documentation.</p>
            </body>
            </html>
            """
        )


@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Health status and system information
    """
    try:
        # Test database connection
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_healthy = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_healthy = False
    
    try:
        # Test Redis connection
        redis = await get_redis_client()
        await redis.ping()
        redis_healthy = True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_healthy = False
    
    overall_healthy = db_healthy and redis_healthy
    
    return {
        "status": "healthy" if overall_healthy else "unhealthy",
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "components": {
            "database": "healthy" if db_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy",
        },
    }


@app.get("/readiness", tags=["health"])
async def readiness_check():
    """
    Readiness check endpoint for Kubernetes.
    
    Returns:
        dict: Readiness status
    """
    # Add more comprehensive checks if needed
    return {"status": "ready"}


@app.get("/liveness", tags=["health"])
async def liveness_check():
    """
    Liveness check endpoint for Kubernetes.
    
    Returns:
        dict: Liveness status
    """
    return {"status": "alive"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_ENV == "development",
        log_config=None,  # Use our custom logging
    )
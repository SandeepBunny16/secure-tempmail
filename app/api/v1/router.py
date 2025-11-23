"""
API v1 Router

Aggregates all API v1 endpoints.
"""

from fastapi import APIRouter

from app.api.v1 import inboxes, messages, health, admin

api_router = APIRouter()

# Include all routers
api_router.include_router(
    inboxes.router,
    prefix="/inboxes",
    tags=["inboxes"],
)

api_router.include_router(
    messages.router,
    prefix="/messages",
    tags=["messages"],
)

api_router.include_router(
    health.router,
    tags=["health"],
)

api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["admin"],
)
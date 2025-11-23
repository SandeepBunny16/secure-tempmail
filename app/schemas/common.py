"""
Common Pydantic schemas used across the application.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Health status")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment (development/production)")
    components: Dict[str, str] = Field(default_factory=dict, description="Component health status")


class ErrorResponse(BaseModel):
    """Error response."""
    
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    detail: Optional[Any] = Field(None, description="Additional error details")


class SuccessResponse(BaseModel):
    """Generic success response."""
    
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
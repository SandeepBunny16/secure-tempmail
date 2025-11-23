"""
Configuration Management

Centralized configuration using Pydantic Settings with environment variables.
Supports validation, type checking, and default values.
"""

import secrets
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden via environment variables.
    Sensitive values should NEVER have defaults.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # ===================================
    # Application Settings
    # ===================================
    APP_ENV: str = Field(default="production", description="Environment: development, staging, production")
    APP_NAME: str = Field(default="SecureTempMail", description="Application name")
    APP_HOST: str = Field(default="0.0.0.0", description="Host to bind to")
    APP_PORT: int = Field(default=8000, description="Port to bind to")
    APP_DOMAIN: str = Field(..., description="Application domain (required)")
    
    # ===================================
    # Security Keys (REQUIRED)
    # ===================================
    SECRET_KEY: str = Field(..., description="Secret key for JWT tokens (required)")
    ENCRYPTION_KEY: str = Field(..., description="Encryption key for message bodies (required)")
    API_KEY: str = Field(..., description="API key for admin endpoints (required)")
    
    # ===================================
    # Database Configuration
    # ===================================
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL host")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port")
    POSTGRES_DB: str = Field(default="tempmail", description="PostgreSQL database name")
    POSTGRES_USER: str = Field(default="tempmail", description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field(..., description="PostgreSQL password (required)")
    
    DATABASE_URL: Optional[str] = Field(default=None, description="Database URL (auto-constructed if not provided)")
    DATABASE_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=40, description="Database connection max overflow")
    DATABASE_ECHO: bool = Field(default=False, description="Echo SQL queries (debug)")
    
    # ===================================
    # Redis Configuration
    # ===================================
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_PASSWORD: str = Field(..., description="Redis password (required)")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    
    REDIS_URL: Optional[str] = Field(default=None, description="Redis URL (auto-constructed if not provided)")
    REDIS_POOL_SIZE: int = Field(default=10, description="Redis connection pool size")
    
    # ===================================
    # Email Settings
    # ===================================
    DEFAULT_TTL_HOURS: int = Field(default=24, ge=1, le=168, description="Default inbox TTL in hours (1-168)")
    MAX_EMAILS_PER_INBOX: int = Field(default=50, ge=1, le=1000, description="Maximum emails per inbox")
    MAX_EMAIL_SIZE_MB: int = Field(default=10, ge=1, le=50, description="Maximum email size in MB")
    ADDRESS_LENGTH: int = Field(default=24, ge=16, le=64, description="Generated address length")
    ADDRESS_PREFIX: str = Field(default="tmp_", description="Address prefix")
    
    # ===================================
    # SMTP Settings
    # ===================================
    SMTP_HOST: str = Field(default="0.0.0.0", description="SMTP server host")
    SMTP_PORT: int = Field(default=8025, description="SMTP server port")
    SMTP_HOSTNAME: Optional[str] = Field(default=None, description="SMTP hostname (defaults to APP_DOMAIN)")
    SMTP_ENABLE_STARTTLS: bool = Field(default=True, description="Enable STARTTLS")
    
    # ===================================
    # Rate Limiting
    # ===================================
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, ge=1, description="Requests per minute per IP")
    RATE_LIMIT_PER_HOUR: int = Field(default=1000, ge=1, description="Requests per hour per IP")
    INBOX_CREATION_LIMIT_PER_HOUR: int = Field(default=10, ge=1, description="Inbox creations per hour per IP")
    
    # ===================================
    # Worker Settings
    # ===================================
    CLEANUP_INTERVAL_MINUTES: int = Field(default=5, ge=1, description="TTL cleanup interval in minutes")
    CLEANUP_BATCH_SIZE: int = Field(default=100, ge=1, description="Batch size for cleanup operations")
    
    # ===================================
    # Logging Configuration
    # ===================================
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format: json or text")
    LOG_FILE: Optional[str] = Field(default=None, description="Log file path")
    
    # ===================================
    # Security Headers
    # ===================================
    ENABLE_CORS: bool = Field(default=True, description="Enable CORS")
    CORS_ORIGINS: List[str] = Field(default=["*"], description="Allowed CORS origins")
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="Allow credentials in CORS")
    CSP_ENABLED: bool = Field(default=True, description="Enable Content Security Policy")
    
    # ===================================
    # Monitoring
    # ===================================
    ENABLE_METRICS: bool = Field(default=True, description="Enable Prometheus metrics")
    METRICS_PORT: int = Field(default=9090, description="Metrics port")
    METRICS_ENDPOINT: str = Field(default="/metrics", description="Metrics endpoint path")
    
    # ===================================
    # Feature Flags
    # ===================================
    ENABLE_DEBUG_TOOLBAR: bool = Field(default=False, description="Enable debug toolbar (dev only)")
    RELOAD_ON_CHANGE: bool = Field(default=False, description="Reload on code changes (dev only)")
    
    # ===================================
    # Validators
    # ===================================
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v, info):
        """Construct DATABASE_URL if not provided."""
        if v:
            return v
        
        values = info.data
        return (
            f"postgresql+asyncpg://{values.get('POSTGRES_USER')}:"
            f"{values.get('POSTGRES_PASSWORD')}@{values.get('POSTGRES_HOST')}:"
            f"{values.get('POSTGRES_PORT')}/{values.get('POSTGRES_DB')}"
        )
    
    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def assemble_redis_url(cls, v, info):
        """Construct REDIS_URL if not provided."""
        if v:
            return v
        
        values = info.data
        password = values.get('REDIS_PASSWORD')
        host = values.get('REDIS_HOST')
        port = values.get('REDIS_PORT')
        db = values.get('REDIS_DB')
        
        if password:
            return f"redis://:{password}@{host}:{port}/{db}"
        return f"redis://{host}:{port}/{db}"
    
    @field_validator("SMTP_HOSTNAME", mode="before")
    @classmethod
    def set_smtp_hostname(cls, v, info):
        """Set SMTP hostname to APP_DOMAIN if not provided."""
        if v:
            return v
        return info.data.get('APP_DOMAIN')
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v
    
    @field_validator("APP_ENV")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment."""
        valid_envs = ["development", "staging", "production"]
        v = v.lower()
        if v not in valid_envs:
            raise ValueError(f"Environment must be one of: {valid_envs}")
        return v
    
    # ===================================
    # Computed Properties
    # ===================================
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.APP_ENV == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.APP_ENV == "production"
    
    @property
    def max_email_size_bytes(self) -> int:
        """Get maximum email size in bytes."""
        return self.MAX_EMAIL_SIZE_MB * 1024 * 1024
    
    @property
    def default_ttl_seconds(self) -> int:
        """Get default TTL in seconds."""
        return self.DEFAULT_TTL_HOURS * 3600


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Using lru_cache ensures settings are loaded only once.
    
    Returns:
        Settings: Application settings
    """
    return Settings()
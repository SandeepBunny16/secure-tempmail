"""
Logging Configuration

Structured logging with JSON output for production.
Supports:
- Multiple log levels
- JSON and text formats
- File and console output
- Request context tracking
"""

import logging
import sys
from typing import Optional

import structlog
from pythonjsonlogger import jsonlogger

from app.config import get_settings


settings = get_settings()


def setup_logging():
    """
    Configure application logging.
    
    Sets up:
    - Log level from settings
    - JSON or text format
    - Console and file handlers
    - Structlog processors
    """
    # Get log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper())
    
    # Configure root logger
    logging.root.setLevel(log_level)
    logging.root.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Format
    if settings.LOG_FORMAT == "json":
        formatter = jsonlogger.JsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s %(pathname)s %(lineno)d",
            rename_fields={
                "levelname": "level",
                "name": "logger",
                "pathname": "file",
                "lineno": "line",
            },
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    
    console_handler.setFormatter(formatter)
    logging.root.addHandler(console_handler)
    
    # File handler (if configured)
    if settings.LOG_FILE:
        try:
            file_handler = logging.FileHandler(settings.LOG_FILE)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logging.root.addHandler(file_handler)
        except Exception as e:
            logging.error(f"Failed to setup file logging: {e}")
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Suppress noisy loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("aiosmtpd").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)


class LoggerAdapter:
    """
    Logger adapter with request context.
    
    Adds request ID and user context to all log messages.
    """
    
    def __init__(self, logger: logging.Logger, request_id: Optional[str] = None):
        """Initialize logger adapter."""
        self.logger = logger
        self.request_id = request_id
        self.extra = {}
        
        if request_id:
            self.extra["request_id"] = request_id
    
    def _log(self, level: int, msg: str, **kwargs):
        """Log message with extra context."""
        extra = {**self.extra, **kwargs.pop("extra", {})}
        self.logger.log(level, msg, extra=extra, **kwargs)
    
    def debug(self, msg: str, **kwargs):
        """Log debug message."""
        self._log(logging.DEBUG, msg, **kwargs)
    
    def info(self, msg: str, **kwargs):
        """Log info message."""
        self._log(logging.INFO, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        """Log warning message."""
        self._log(logging.WARNING, msg, **kwargs)
    
    def error(self, msg: str, **kwargs):
        """Log error message."""
        self._log(logging.ERROR, msg, **kwargs)
    
    def critical(self, msg: str, **kwargs):
        """Log critical message."""
        self._log(logging.CRITICAL, msg, **kwargs)
    
    def exception(self, msg: str, **kwargs):
        """Log exception with traceback."""
        self.logger.exception(msg, extra=self.extra, **kwargs)
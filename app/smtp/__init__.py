"""
SMTP Module

SMTP server implementation for receiving emails.
"""

from app.smtp.server import start_smtp_server
from app.smtp.handler import TempMailHandler
from app.smtp.processor import EmailProcessor

__all__ = [
    "start_smtp_server",
    "TempMailHandler",
    "EmailProcessor",
]
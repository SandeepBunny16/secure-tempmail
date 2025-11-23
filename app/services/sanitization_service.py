"""
HTML Sanitization Service

Provides XSS-safe HTML cleaning using Bleach library.
"""

import bleach
from typing import List, Optional

from app.core.exceptions import SanitizationException
from app.core.logging import get_logger

logger = get_logger(__name__)


class SanitizationService:
    """Service for sanitizing HTML content."""
    
    # Allowed HTML tags (safe subset)
    ALLOWED_TAGS = [
        'a', 'abbr', 'acronym', 'b', 'blockquote', 'br', 'code', 'div',
        'em', 'i', 'li', 'ol', 'p', 'pre', 'span', 'strong', 'ul',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'img', 'hr',
    ]
    
    # Allowed HTML attributes
    ALLOWED_ATTRIBUTES = {
        '*': ['class', 'id'],
        'a': ['href', 'title', 'rel'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'abbr': ['title'],
        'acronym': ['title'],
        'table': ['border', 'cellpadding', 'cellspacing'],
        'th': ['colspan', 'rowspan'],
        'td': ['colspan', 'rowspan'],
    }
    
    # Allowed URL schemes
    ALLOWED_PROTOCOLS = ['http', 'https', 'mailto', 'data']
    
    def __init__(self):
        """Initialize sanitization service with safe defaults."""
        self.cleaner = bleach.Cleaner(
            tags=self.ALLOWED_TAGS,
            attributes=self.ALLOWED_ATTRIBUTES,
            protocols=self.ALLOWED_PROTOCOLS,
            strip=True,  # Strip disallowed tags
            strip_comments=True,  # Remove HTML comments
        )
    
    def sanitize_html(self, html: str) -> str:
        """
        Sanitize HTML content to prevent XSS attacks.
        
        Args:
            html: Raw HTML string
        
        Returns:
            str: Sanitized HTML safe for rendering
        
        Raises:
            SanitizationException: If sanitization fails
        """
        if not html:
            return ""
        
        try:
            # Clean HTML
            clean_html = self.cleaner.clean(html)
            
            # Additional safety: linkify URLs but escape them
            clean_html = bleach.linkify(
                clean_html,
                parse_email=True,
                callbacks=[self._set_link_attributes],
            )
            
            return clean_html
            
        except Exception as e:
            logger.error(f"HTML sanitization failed: {str(e)}")
            raise SanitizationException(
                message="Failed to sanitize HTML content",
                detail={"error": str(e)}
            )
    
    def sanitize_text(self, text: str) -> str:
        """
        Sanitize plain text by escaping HTML entities.
        
        Args:
            text: Plain text string
        
        Returns:
            str: Escaped text safe for HTML display
        """
        if not text:
            return ""
        
        return bleach.clean(text, tags=[], strip=True)
    
    def _set_link_attributes(self, attrs, new=False):
        """
        Callback to set link attributes for security.
        
        Adds rel="noopener noreferrer" to all links.
        """
        # Get href
        href_key = (None, 'href')
        if href_key in attrs:
            # Add security attributes
            attrs[(None, 'rel')] = 'noopener noreferrer'
            
            # Open external links in new tab
            if attrs[href_key].startswith('http'):
                attrs[(None, 'target')] = '_blank'
        
        return attrs
    
    def strip_tags(self, html: str) -> str:
        """
        Strip all HTML tags, leaving only text.
        
        Args:
            html: HTML string
        
        Returns:
            str: Plain text with no HTML
        """
        return bleach.clean(html, tags=[], strip=True)
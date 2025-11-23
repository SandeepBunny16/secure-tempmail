"""
Security Module

Provides encryption, authentication, and security utilities:
- Fernet symmetric encryption (AES-256)
- JWT token generation and verification
- Password hashing with bcrypt
- Secure random string generation
"""

import base64
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.core.exceptions import EncryptionException, InvalidTokenException


settings = get_settings()


# ===================================
# Password Hashing
# ===================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
    
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
    
    Returns:
        bool: True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


# ===================================
# Encryption/Decryption
# ===================================

class EncryptionService:
    """
    Encryption service using Fernet (AES-256).
    
    Provides secure encryption and decryption of sensitive data.
    Uses the ENCRYPTION_KEY from settings.
    """
    
    def __init__(self):
        """Initialize encryption service with key from settings."""
        try:
            # Derive Fernet key from settings
            key = self._derive_key(settings.ENCRYPTION_KEY)
            self.cipher = Fernet(key)
        except Exception as e:
            raise EncryptionException(
                message="Failed to initialize encryption service",
                detail={"error": str(e)}
            )
    
    def _derive_key(self, key_material: str) -> bytes:
        """
        Derive a Fernet-compatible key from key material.
        
        Args:
            key_material: Key material (hex string)
        
        Returns:
            bytes: Base64-encoded 32-byte key
        """
        # Convert hex string to bytes
        key_bytes = bytes.fromhex(key_material)
        
        # Ensure 32 bytes (for AES-256)
        if len(key_bytes) < 32:
            # Pad with zeros if too short
            key_bytes = key_bytes + b'\x00' * (32 - len(key_bytes))
        elif len(key_bytes) > 32:
            # Truncate if too long
            key_bytes = key_bytes[:32]
        
        # Base64 encode for Fernet
        return base64.urlsafe_b64encode(key_bytes)
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt data.
        
        Args:
            data: Plain text data
        
        Returns:
            str: Encrypted data (base64 encoded)
        
        Raises:
            EncryptionException: If encryption fails
        """
        try:
            encrypted = self.cipher.encrypt(data.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
        except Exception as e:
            raise EncryptionException(
                message="Encryption failed",
                detail={"error": str(e)}
            )
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt data.
        
        Args:
            encrypted_data: Encrypted data (base64 encoded)
        
        Returns:
            str: Decrypted plain text
        
        Raises:
            EncryptionException: If decryption fails
        """
        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted = self.cipher.decrypt(decoded)
            return decrypted.decode('utf-8')
        except Exception as e:
            raise EncryptionException(
                message="Decryption failed",
                detail={"error": str(e)}
            )
    
    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """
        Encrypt a dictionary.
        
        Args:
            data: Dictionary to encrypt
        
        Returns:
            str: Encrypted JSON string
        """
        import json
        json_str = json.dumps(data)
        return self.encrypt(json_str)
    
    def decrypt_dict(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Decrypt to a dictionary.
        
        Args:
            encrypted_data: Encrypted data
        
        Returns:
            dict: Decrypted dictionary
        """
        import json
        decrypted = self.decrypt(encrypted_data)
        return json.loads(decrypted)


# ===================================
# JWT Tokens
# ===================================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in token
        expires_delta: Token expiration time (default: 24 hours)
    
    Returns:
        str: JWT token
    """
    to_encode = data.copy()
    
    # Set expiration
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    })
    
    # Encode token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token to verify
    
    Returns:
        dict: Decoded token payload
    
    Raises:
        InvalidTokenException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        
        # Verify token type
        if payload.get("type") != "access":
            raise InvalidTokenException(
                detail={"error": "Invalid token type"}
            )
        
        return payload
        
    except JWTError as e:
        raise InvalidTokenException(
            detail={"error": str(e)}
        )


# ===================================
# Random String Generation
# ===================================

def generate_random_string(
    length: int = 32,
    include_uppercase: bool = True,
    include_lowercase: bool = True,
    include_digits: bool = True,
    include_special: bool = False,
) -> str:
    """
    Generate a cryptographically secure random string.
    
    Args:
        length: Length of string
        include_uppercase: Include uppercase letters
        include_lowercase: Include lowercase letters
        include_digits: Include digits
        include_special: Include special characters
    
    Returns:
        str: Random string
    """
    chars = ''
    
    if include_uppercase:
        chars += string.ascii_uppercase
    if include_lowercase:
        chars += string.ascii_lowercase
    if include_digits:
        chars += string.digits
    if include_special:
        chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    if not chars:
        raise ValueError("At least one character type must be included")
    
    return ''.join(secrets.choice(chars) for _ in range(length))


def generate_inbox_address(
    domain: str,
    prefix: str = "tmp_",
    length: int = 24,
) -> str:
    """
    Generate a random email address for an inbox.
    
    Args:
        domain: Email domain
        prefix: Address prefix
        length: Length of random part
    
    Returns:
        str: Email address (e.g., tmp_abc123xyz456@domain.com)
    """
    random_part = generate_random_string(
        length=length,
        include_uppercase=False,
        include_lowercase=True,
        include_digits=True,
        include_special=False,
    )
    
    return f"{prefix}{random_part}@{domain}"


def generate_inbox_id() -> str:
    """
    Generate a unique inbox ID.
    
    Returns:
        str: Inbox ID (UUID-like)
    """
    import uuid
    return str(uuid.uuid4())


def generate_message_id() -> str:
    """
    Generate a unique message ID.
    
    Returns:
        str: Message ID (UUID-like)
    """
    import uuid
    return str(uuid.uuid4())


# ===================================
# API Key Validation
# ===================================

def verify_api_key(api_key: str) -> bool:
    """
    Verify API key.
    
    Args:
        api_key: API key to verify
    
    Returns:
        bool: True if valid
    """
    return secrets.compare_digest(api_key, settings.API_KEY)


# ===================================
# CSRF Protection (Optional)
# ===================================

def generate_csrf_token() -> str:
    """
    Generate a CSRF token.
    
    Returns:
        str: CSRF token
    """
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, expected: str) -> bool:
    """
    Verify CSRF token.
    
    Args:
        token: Token to verify
        expected: Expected token value
    
    Returns:
        bool: True if valid
    """
    return secrets.compare_digest(token, expected)
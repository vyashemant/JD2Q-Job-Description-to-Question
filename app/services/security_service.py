"""
JD2Q Security Service
Handles encryption, OTP validation, and security utilities.
"""
import os
import secrets
from datetime import datetime, timedelta
from cryptography.fernet import Fernet, InvalidToken
from flask import current_app, session


class SecurityService:
    """Security utilities for encryption, validation, and session management."""
    
    @staticmethod
    def get_fernet():
        """
        Get Fernet cipher instance from app config.
        
        Returns:
            Fernet cipher instance
            
        Raises:
            ValueError: If FERNET_SECRET_KEY not configured
        """
        key = current_app.config.get('FERNET_SECRET_KEY')
        if not key:
            raise ValueError("FERNET_SECRET_KEY not configured")
        
        # Ensure key is bytes
        if isinstance(key, str):
            key = key.encode()
        
        return Fernet(key)
    
    @staticmethod
    def encrypt_api_key(api_key: str) -> str:
        """
        Encrypt an API key using Fernet symmetric encryption.
        
        Args:
            api_key: Plaintext API key to encrypt
            
        Returns:
            Base64-encoded encrypted key
        """
        fernet = SecurityService.get_fernet()
        encrypted = fernet.encrypt(api_key.encode())
        return encrypted.decode()
    
    @staticmethod
    def decrypt_api_key(encrypted_key: str) -> str:
        """
        Decrypt an API key.
        
        Args:
            encrypted_key: Base64-encoded encrypted key
            
        Returns:
            Plaintext API key
            
        Raises:
            ValueError: If decryption fails
        """
        try:
            fernet = SecurityService.get_fernet()
            decrypted = fernet.decrypt(encrypted_key.encode())
            return decrypted.decode()
        except InvalidToken:
            raise ValueError("Failed to decrypt API key - invalid or corrupted data")
    
    @staticmethod
    def mask_api_key(api_key: str, visible_chars: int = 4) -> str:
        """
        Mask an API key for display purposes.
        
        Args:
            api_key: API key to mask
            visible_chars: Number of trailing characters to show
            
        Returns:
            Masked key (e.g., "****...xyz123")
        """
        if len(api_key) <= visible_chars:
            return "*" * len(api_key)
        
        mask_length = len(api_key) - visible_chars
        return ("*" * min(mask_length, 20)) + api_key[-visible_chars:]
    
    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """
        Validate password meets complexity requirements.
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"
        
        return True, ""
    
    @staticmethod
    def create_session_token() -> str:
        """
        Generate a secure random session token.
        
        Returns:
            32-character hex token
        """
        return secrets.token_hex(32)
    
    @staticmethod
    def set_user_session(user_id: str, email: str, access_token: str = None):
        """
        Set user session data.
        
        Args:
            user_id: Supabase user ID
            email: User email
            access_token: Optional Supabase access token
        """
        session['user_id'] = user_id
        session['email'] = email
        if access_token:
            session['access_token'] = access_token
        session['logged_in_at'] = datetime.utcnow().isoformat()
        session.permanent = True
    
    @staticmethod
    def clear_session():
        """Clear all session data."""
        session.clear()
    
    @staticmethod
    def get_session_user_id() -> str | None:
        """
        Get current user ID from session.
        
        Returns:
            User ID or None if not authenticated
        """
        return session.get('user_id')
    
    @staticmethod
    def get_session_access_token() -> str | None:
        """
        Get Supabase access token from session.
        
        Returns:
            Access token or None if not present
        """
        return session.get('access_token')
    
    @staticmethod
    def is_authenticated() -> bool:
        """
        Check if user is authenticated.
        
        Returns:
            True if user is logged in
        """
        return 'user_id' in session and 'email' in session


class OTPService:
    """OTP generation and validation service."""
    
    # In-memory OTP storage (for production, use Redis or database)
    _otp_store = {}
    
    @staticmethod
    def generate_otp(email: str) -> str:
        """
        Generate a 4-digit OTP code.
        
        Note: In production with Supabase Auth, OTP generation is handled
        by Supabase. This method is for testing/reference only.
        
        Args:
            email: Email address to associate with OTP
            
        Returns:
            4-digit OTP code
        """
        otp = str(secrets.randbelow(1000000)).zfill(6)
        
        # Store OTP with expiry
        expiry_minutes = current_app.config.get('OTP_EXPIRY_MINUTES', 10)
        expiry = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        OTPService._otp_store[email] = {
            'code': otp,
            'expiry': expiry,
            'attempts': 0
        }
        
        return otp
    
    @staticmethod
    def verify_otp(email: str, code: str) -> tuple[bool, str]:
        """
        Verify OTP code.
        
        Note: In production with Supabase Auth, OTP verification is handled
        by Supabase. This method is for testing/reference only.
        
        Args:
            email: Email address
            code: OTP code to verify
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if email not in OTPService._otp_store:
            return False, "No OTP found for this email"
        
        otp_data = OTPService._otp_store[email]
        
        # Check expiry
        if datetime.utcnow() > otp_data['expiry']:
            del OTPService._otp_store[email]
            return False, "OTP has expired"
        
        # Check attempts
        max_attempts = current_app.config.get('MAX_OTP_ATTEMPTS', 5)
        if otp_data['attempts'] >= max_attempts:
            del OTPService._otp_store[email]
            return False, "Maximum verification attempts exceeded"
        
        # Verify code
        if otp_data['code'] != code:
            otp_data['attempts'] += 1
            return False, f"Invalid OTP code ({max_attempts - otp_data['attempts']} attempts remaining)"
        
        # Valid OTP - remove from store
        del OTPService._otp_store[email]
        return True, ""
    
    @staticmethod
    def clear_otp(email: str):
        """Clear OTP for email."""
        if email in OTPService._otp_store:
            del OTPService._otp_store[email]


def validate_jd_word_count(text: str) -> tuple[bool, int]:
    """
    Validate job description word count.
    
    Args:
        text: Job description text
        
    Returns:
        Tuple of (is_valid, word_count)
    """
    if not text or not text.strip():
        return False, 0
    
    words = text.split()
    word_count = len(words)
    max_words = current_app.config.get('MAX_JD_WORDS', 1500)
    
    return word_count <= max_words, word_count

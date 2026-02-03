"""
Tests for security service including encryption and validation.
"""
import pytest
from app.services.security_service import SecurityService, validate_jd_word_count
from cryptography.fernet import Fernet


def test_encrypt_decrypt_api_key(app):
    """Test API key encryption and decryption."""
    with app.app_context():
        original_key = "AIzaSyDEMOKEY123456789"
        
        # Encrypt
        encrypted = SecurityService.encrypt_api_key(original_key)
        assert encrypted != original_key
        assert len(encrypted) > 0
        
        # Decrypt
        decrypted = SecurityService.decrypt_api_key(encrypted)
        assert decrypted == original_key


def test_mask_api_key():
    """Test API key masking."""
    key = "AIzaSyDEMOKEY123456789"
    
    masked = SecurityService.mask_api_key(key, visible_chars=4)
    assert "6789" in masked
    assert "AIza" not in masked
    assert "*" in masked


def test_validate_password_strength():
    """Test password complexity validation."""
    # Valid password
    is_valid, msg = SecurityService.validate_password_strength("ValidPass123")
    assert is_valid is True
    
    # Too short
    is_valid, msg = SecurityService.validate_password_strength("Short1")
    assert is_valid is False
    assert "8 characters" in msg
    
    # No uppercase
    is_valid, msg = SecurityService.validate_password_strength("lowercase123")
    assert is_valid is False
    assert "uppercase" in msg
    
    # No lowercase
    is_valid, msg = SecurityService.validate_password_strength("UPPERCASE123")
    assert is_valid is False
    assert "lowercase" in msg
    
    # No digit
    is_valid, msg = SecurityService.validate_password_strength("NoDigits")
    assert is_valid is False
    assert "digit" in msg


def test_validate_jd_word_count(app):
    """Test job description word count validation."""
    with app.app_context():
        # Valid JD
        jd = " ".join(["word"] * 1000)
        is_valid, count = validate_jd_word_count(jd)
        assert is_valid is True
        assert count == 1000
        
        # Too long
        jd = " ".join(["word"] * 2000)
        is_valid, count = validate_jd_word_count(jd)
        assert is_valid is False
        assert count == 2000
        
        # Empty
        is_valid, count = validate_jd_word_count("")
        assert is_valid is False
        assert count == 0


def test_session_token_generation():
    """Test secure session token generation."""
    token1 = SecurityService.create_session_token()
    token2 = SecurityService.create_session_token()
    
    assert len(token1) == 64  # 32 bytes = 64 hex chars
    assert token1 != token2  # Should be unique
    assert all(c in '0123456789abcdef' for c in token1)  # Hex chars only

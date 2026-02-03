"""
JD2Q Application Configuration
Manages environment-specific settings and secrets.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration with common settings."""
    
    # Flask Core
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32)
    
    # Supabase
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    
    # Encryption
    FERNET_SECRET_KEY = os.environ.get('FERNET_SECRET_KEY')
    
    # Session Configuration
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True') == 'True'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # No time limit for CSRF tokens
    WTF_CSRF_SSL_STRICT = True  # In production, require HTTPS
    
    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '100/hour')
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_STRATEGY = 'fixed-window'
    
    # Application Settings
    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
    MAX_JD_WORDS = int(os.environ.get('MAX_JD_WORDS', 1500))
    MIN_QUESTIONS = int(os.environ.get('MIN_QUESTIONS', 15))
    MAX_OTP_ATTEMPTS = int(os.environ.get('MAX_OTP_ATTEMPTS', 5))
    OTP_EXPIRY_MINUTES = int(os.environ.get('OTP_EXPIRY_MINUTES', 10))
    
    # File Upload Settings
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max file upload
    ALLOWED_AVATAR_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Gemini AI (Pulled from database per user, this is a fallback only)
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    
    # Sentry (optional)
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    
    @staticmethod
    def validate():
        """Validate required configuration variables."""
        required = [
            'SUPABASE_URL',
            'SUPABASE_ANON_KEY',
            'SUPABASE_SERVICE_ROLE_KEY',
            'FERNET_SECRET_KEY'
        ]
        
        missing = [var for var in required if not os.environ.get(var)]
        
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Please check your .env file or environment configuration."
            )


class DevelopmentConfig(Config):
    """Development environment configuration."""
    
    DEBUG = True
    ENV = 'development'
    
    # Disable secure cookie requirement for local development
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_SSL_STRICT = False
    
    # More lenient rate limiting for development
    RATELIMIT_DEFAULT = '1000/hour'


class ProductionConfig(Config):
    """Production environment configuration."""
    
    DEBUG = False
    ENV = 'production'
    
    # Enforce secure settings
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_SSL_STRICT = True
    
    # Strict rate limiting
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '5/minute')
    
    @classmethod
    def init_app(cls, app):
        """Production-specific initialization."""
        Config.validate()
        
        # Initialize Sentry if DSN is provided
        if cls.SENTRY_DSN:
            try:
                import sentry_sdk
                from sentry_sdk.integrations.flask import FlaskIntegration
                
                sentry_sdk.init(
                    dsn=cls.SENTRY_DSN,
                    integrations=[FlaskIntegration()],
                    traces_sample_rate=0.1
                )
            except ImportError:
                pass


class TestingConfig(Config):
    """Testing environment configuration."""
    
    TESTING = True
    ENV = 'testing'
    
    # Disable CSRF for easier testing
    WTF_CSRF_ENABLED = False
    
    # Disable rate limiting for tests
    RATELIMIT_ENABLED = False
    
    # Use in-memory storage for tests
    RATELIMIT_STORAGE_URL = 'memory://'
    
    # Override with test values
    SUPABASE_URL = os.environ.get('TEST_SUPABASE_URL', 'http://localhost:54321')


# Configuration dictionary
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    """
    Get configuration object by name.
    
    Args:
        config_name: Configuration name (development, production, testing)
    
    Returns:
        Configuration class
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    return config_map.get(config_name, config_map['default'])

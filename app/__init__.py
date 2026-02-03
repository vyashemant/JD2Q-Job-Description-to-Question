"""
JD2Q Flask Application Factory
Implements app factory pattern with security, extensions, and blueprints.
"""
from flask import Flask, render_template, session
from app.config import get_config
from app.extensions import csrf, limiter
import os


def create_app(config_name=None):
    """
    Application factory for creating Flask app instances.
    
    Args:
        config_name: Configuration name (development, production, testing)
                    Defaults to FLASK_ENV environment variable
    
    Returns:
        Configured Flask application instance
    """
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "production")
    
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Initialize extensions
    csrf.init_app(app)
    limiter.init_app(app)
    
    # Configure security headers
    @app.after_request
    def set_security_headers(response):
        """Add security headers to all responses."""
        # Content Security Policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://*.supabase.co;"
        )
        
        # HSTS - Force HTTPS (only in production)
        if app.config.get('ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Prevent MIME sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Prevent framing
        response.headers['X-Frame-Options'] = 'DENY'
        
        # XSS Protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        return response
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors."""
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(429)
    def ratelimit_error(error):
        """Handle rate limit errors."""
        return render_template('errors/429.html'), 429
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 forbidden errors."""
        return render_template('errors/403.html'), 403
    
    # Register blueprints
    register_blueprints(app)
    
    # Context processors
    @app.context_processor
    def inject_user():
        """Inject current user into all templates."""
        from app.services.supabase_service import get_current_user
        user = get_current_user()
        return dict(current_user=user)
    
    return app


def register_blueprints(app):
    """
    Register all application blueprints.
    
    Args:
        app: Flask application instance
    """
    # Import blueprints
    from app.routes.web import web_bp
    from app.routes.auth import auth_bp
    from app.routes.profile import profile_bp
    from app.routes.generation import generation_bp
    from app.routes.history import history_bp
    
    # Register blueprints with URL prefixes
    app.register_blueprint(web_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(profile_bp, url_prefix='/profile')
    app.register_blueprint(generation_bp, url_prefix='/generate')
    app.register_blueprint(history_bp, url_prefix='/history')

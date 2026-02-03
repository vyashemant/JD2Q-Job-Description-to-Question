#!/usr/bin/env python
"""
JD2Q Application Entry Point
Serves as both Vercel entry point and local development server.
"""
import os
from app import create_app

# Create Flask application instance
app = create_app()

# Vercel requires the app instance to be named 'app'
# For local development, run with: python run.py
if __name__ == "__main__":
    # Development server configuration
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug
    )

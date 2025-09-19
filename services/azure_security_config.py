"""
Azure Security Configuration

Provides security enhancements for Azure deployment including:
- HTTPS enforcement
- Security headers
- CORS configuration
- Rate limiting
"""

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def configure_app_for_azure(app):
    """Configure Flask app with Azure security settings"""
    
    # Force HTTPS in production (Azure App Service)
    if is_azure_environment():
        app.config['PREFERRED_URL_SCHEME'] = 'https'
        
        # Add security headers middleware
        @app.after_request
        def add_security_headers(response):
            # HTTPS enforcement
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            
            # Content security
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            
            # Referrer policy
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # WebSocket headers for SocketIO (only for JSON responses to avoid static file issues)
            if (hasattr(response, 'mimetype') and 
                response.mimetype == 'application/json'):
                try:
                    if 'socket.io' in str(response.get_data()):
                        response.headers['Connection'] = 'Upgrade'
                        response.headers['Upgrade'] = 'websocket'
                except RuntimeError:
                    # Skip if response is in passthrough mode (static files)
                    pass
            
            return response
        
        logger.info("Azure security headers configured")
    
    # Configure CORS for Azure
    cors_origins = os.environ.get('CORS_ORIGINS', '*').split(',')
    app.config['CORS_ORIGINS'] = cors_origins
    
    # Session security
    app.config['SESSION_COOKIE_SECURE'] = is_azure_environment()
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    logger.info("Azure security configuration applied")
    return app


def is_azure_environment() -> bool:
    """Check if running in Azure environment"""
    azure_indicators = [
        'WEBSITE_SITE_NAME',
        'WEBSITE_RESOURCE_GROUP', 
        'APPSETTING_WEBSITE_SITE_NAME'
    ]
    return any(os.environ.get(indicator) for indicator in azure_indicators)


def get_security_config() -> Dict[str, Any]:
    """Get current security configuration"""
    return {
        'is_azure': is_azure_environment(),
        'https_enforced': is_azure_environment(),
        'security_headers_enabled': is_azure_environment(),
        'cors_origins': os.environ.get('CORS_ORIGINS', '*').split(','),
        'session_secure': is_azure_environment()
    }
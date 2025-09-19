"""
Azure WebSocket Configuration

Handles Azure App Service specific WebSocket configuration and optimizations.
"""

import os
import logging

logger = logging.getLogger(__name__)


def is_azure_app_service():
    """Check if running on Azure App Service"""
    return bool(os.environ.get('WEBSITE_SITE_NAME')) or bool(os.environ.get('APPSETTING_WEBSITE_SITE_NAME'))


def get_azure_websocket_config():
    """Get Azure-optimized WebSocket configuration"""
    if is_azure_app_service():
        return {
            # Use polling first for better Azure compatibility
            'transports': ['polling', 'websocket'],
            
            # Longer timeouts for Azure's proxy layer
            'ping_timeout': 60,
            'ping_interval': 25,
            
            # Connection settings
            'upgrade': True,
            'rememberUpgrade': False,  # Don't cache upgrade on Azure
            
            # Reconnection settings
            'reconnection': True,
            'reconnectionAttempts': 5,
            'reconnectionDelay': 2000,
            'reconnectionDelayMax': 10000,
            
            # Azure-specific settings
            'forceNew': True,
            'timeout': 10000,
            
            # CORS settings
            'cors_allowed_origins': "*",
            'async_mode': 'threading'  # Use threading for better Azure compatibility
        }
    else:
        # Local development settings
        return {
            'transports': ['websocket', 'polling'],
            'ping_timeout': 30,
            'ping_interval': 10,
            'upgrade': True,
            'rememberUpgrade': True,
            'reconnection': True,
            'reconnectionAttempts': 3,
            'reconnectionDelay': 1000,
            'timeout': 5000,
            'cors_allowed_origins': "*",
            'async_mode': 'threading'
        }


def configure_azure_headers(app):
    """Configure Azure-specific headers for WebSocket support"""
    # Note: Headers are now handled in azure_security_config.py
    # to avoid conflicts with multiple after_request handlers
    return app


def get_azure_socketio_kwargs():
    """Get SocketIO initialization kwargs for Azure"""
    config = get_azure_websocket_config()
    
    if is_azure_app_service():
        return {
            'cors_allowed_origins': config['cors_allowed_origins'],
            'async_mode': 'threading',  # Use threading for Azure compatibility
            'transports': config['transports'],
            'ping_timeout': config['ping_timeout'],
            'ping_interval': config['ping_interval'],
            'logger': True,
            'engineio_logger': False
        }
    else:
        return {
            'cors_allowed_origins': config['cors_allowed_origins'],
            'async_mode': config['async_mode'],
            'logger': True,
            'engineio_logger': True
        }
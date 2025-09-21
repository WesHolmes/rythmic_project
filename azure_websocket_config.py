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
            # Use both transports for better performance
            'transports': ['websocket', 'polling'],
            
            # Optimized timeouts for better performance
            'ping_timeout': 60,  # Reduced for faster failure detection
            'ping_interval': 25,  # Reduced for better responsiveness
            
            # Connection settings - allow upgrades for better performance
            'upgrade': True,
            'rememberUpgrade': True,  # Cache successful upgrades
            
            # Reconnection settings - more aggressive for better UX
            'reconnection': True,
            'reconnectionAttempts': 5,  # Increased for better reliability
            'reconnectionDelay': 5000,  # Start with 5 seconds
            'reconnectionDelayMax': 20000,  # Cap at 20 seconds
            
            # Azure-specific settings - less aggressive
            'forceNew': False,  # Don't force new connections unnecessarily
            'timeout': 15000,  # Increased timeout for Azure proxy layer
            
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
            'engineio_logger': False,
            'always_connect': False,  # Don't auto-connect
            'reconnection': True,
            'reconnection_attempts': 3,  # Reduced for Azure
            'reconnection_delay': 10000,  # Start with 10 seconds
            'reconnection_delay_max': 30000  # Cap at 30 seconds
        }
    else:
        return {
            'cors_allowed_origins': config['cors_allowed_origins'],
            'async_mode': config['async_mode'],
            'logger': True,
            'engineio_logger': True,
            'always_connect': False,
            'reconnection': True,
            'reconnection_attempts': 3,
            'reconnection_delay': 1000
        }
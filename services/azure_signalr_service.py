"""
Azure SignalR Service Integration

Provides real-time communication capabilities using Azure SignalR Service
with fallback to local WebSocket implementation.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class AzureSignalRService:
    """Azure SignalR Service integration"""
    
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string or os.environ.get('AZURE_SIGNALR_CONNECTION_STRING')
        self.enabled = bool(self.connection_string)
        self.client = None
        self.fallback_handler = None
        
        if self.enabled:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Azure SignalR client"""
        try:
            # Try to import Azure SignalR SDK
            from azure.messaging.webpubsubservice import WebPubSubServiceClient
            
            # Parse connection string to get endpoint and access key
            endpoint, access_key = self._parse_connection_string()
            
            if endpoint and access_key:
                self.client = WebPubSubServiceClient(
                    endpoint=endpoint,
                    hub='projectHub',  # Hub name for project collaboration
                    credential=access_key
                )
                logger.info("Azure SignalR Service client initialized successfully")
            else:
                logger.error("Invalid Azure SignalR connection string format")
                self.enabled = False
                
        except ImportError:
            logger.warning("Azure SignalR SDK not available, using fallback")
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize Azure SignalR client: {e}")
            self.enabled = False
    
    def _parse_connection_string(self) -> tuple:
        """Parse Azure SignalR connection string"""
        try:
            if not self.connection_string:
                return None, None
            
            # Parse connection string format: Endpoint=https://...;AccessKey=...
            parts = self.connection_string.split(';')
            endpoint = None
            access_key = None
            
            for part in parts:
                if part.startswith('Endpoint='):
                    endpoint = part.replace('Endpoint=', '')
                elif part.startswith('AccessKey='):
                    access_key = part.replace('AccessKey=', '')
            
            return endpoint, access_key
            
        except Exception as e:
            logger.error(f"Error parsing SignalR connection string: {e}")
            return None, None
    
    def is_available(self) -> bool:
        """Check if Azure SignalR Service is available"""
        return self.enabled and self.client is not None
    
    def set_fallback_handler(self, handler):
        """Set fallback handler for when Azure SignalR is not available"""
        self.fallback_handler = handler
    
    def send_to_user(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Send message to specific user"""
        if self.is_available():
            return self._send_via_azure(user_id=user_id, message=message)
        elif self.fallback_handler:
            return self._send_via_fallback(user_id=user_id, message=message)
        return False
    
    def send_to_group(self, group_id: str, message: Dict[str, Any]) -> bool:
        """Send message to group (project collaborators)"""
        if self.is_available():
            return self._send_via_azure(group_id=group_id, message=message)
        elif self.fallback_handler:
            return self._send_via_fallback(group_id=group_id, message=message)
        return False
    
    def add_user_to_group(self, user_id: str, group_id: str) -> bool:
        """Add user to group for project collaboration"""
        if self.is_available():
            try:
                self.client.add_user_to_group(
                    group=group_id,
                    user_id=user_id
                )
                logger.info(f"Added user {user_id} to group {group_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to add user to group: {e}")
                return False
        return True  # Fallback handles group management differently
    
    def remove_user_from_group(self, user_id: str, group_id: str) -> bool:
        """Remove user from group"""
        if self.is_available():
            try:
                self.client.remove_user_from_group(
                    group=group_id,
                    user_id=user_id
                )
                logger.info(f"Removed user {user_id} from group {group_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to remove user from group: {e}")
                return False
        return True
    
    def _send_via_azure(self, message: Dict[str, Any], user_id: str = None, group_id: str = None) -> bool:
        """Send message via Azure SignalR Service"""
        try:
            message_data = {
                'type': message.get('type', 'message'),
                'data': message.get('data', {}),
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'azure_signalr'
            }
            
            if user_id:
                self.client.send_to_user(
                    user_id=user_id,
                    message=message_data
                )
                logger.debug(f"Message sent to user {user_id} via Azure SignalR")
            elif group_id:
                self.client.send_to_group(
                    group=group_id,
                    message=message_data
                )
                logger.debug(f"Message sent to group {group_id} via Azure SignalR")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message via Azure SignalR: {e}")
            return False
    
    def _send_via_fallback(self, message: Dict[str, Any], user_id: str = None, group_id: str = None) -> bool:
        """Send message via fallback handler (local WebSocket)"""
        try:
            if not self.fallback_handler:
                return False
            
            if user_id:
                # Convert user_id to int for fallback handler
                user_id_int = int(user_id) if user_id.isdigit() else None
                if user_id_int and hasattr(self.fallback_handler, 'send_to_user'):
                    self.fallback_handler.send_to_user(user_id_int, group_id or 'default', message)
                    return True
            elif group_id:
                # Broadcast to project (group_id is project_id)
                project_id = int(group_id) if group_id.isdigit() else None
                if project_id and hasattr(self.fallback_handler, 'broadcast_update'):
                    self.fallback_handler.broadcast_update(project_id, message.get('type', 'message'), message.get('data', {}))
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to send message via fallback: {e}")
            return False
    
    def get_connection_info(self, user_id: str, group_id: str = None) -> Dict[str, Any]:
        """Get connection information for client"""
        if self.is_available():
            try:
                # Generate access token for user
                token = self.client.get_client_access_token(
                    user_id=user_id,
                    groups=[group_id] if group_id else []
                )
                
                endpoint, _ = self._parse_connection_string()
                
                return {
                    'type': 'azure_signalr',
                    'endpoint': endpoint,
                    'accessToken': token['token'],
                    'url': token['url'],
                    'hub': 'projectHub'
                }
                
            except Exception as e:
                logger.error(f"Failed to get connection info: {e}")
                return self._get_fallback_connection_info()
        else:
            return self._get_fallback_connection_info()
    
    def _get_fallback_connection_info(self) -> Dict[str, Any]:
        """Get fallback connection information"""
        return {
            'type': 'local_websocket',
            'endpoint': '/socket.io',
            'namespace': '/project'
        }
    
    def get_flask_socketio_config(self) -> Dict[str, Any]:
        """Get Flask-SocketIO configuration for Azure compatibility"""
        if self.is_available():
            return {
                'cors_allowed_origins': "*",
                'async_mode': 'threading',
                'logger': True,
                'engineio_logger': False,
                'transport': ['websocket', 'polling'],
                'azure_signalr': True
            }
        else:
            return {
                'cors_allowed_origins': "*",
                'async_mode': 'threading',
                'logger': True,
                'engineio_logger': False
            }


def create_signalr_service(connection_string: str = None, fallback_handler=None) -> AzureSignalRService:
    """Create and configure Azure SignalR Service"""
    service = AzureSignalRService(connection_string)
    if fallback_handler:
        service.set_fallback_handler(fallback_handler)
    return service
"""
Azure Service Bus Integration

Provides reliable message queuing and event-driven architecture
using Azure Service Bus with fallback to in-memory queues.
"""

import os
import json
import logging
import asyncio
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ServiceBusMessage:
    """Service Bus message structure"""
    message_type: str
    data: Dict[str, Any]
    project_id: Optional[int] = None
    user_id: Optional[int] = None
    timestamp: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        if not self.correlation_id:
            import uuid
            self.correlation_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceBusMessage':
        """Create from dictionary"""
        return cls(**data)


class AzureServiceBusService:
    """Azure Service Bus integration for reliable message queuing"""
    
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string or os.environ.get('AZURE_SERVICE_BUS_CONNECTION_STRING')
        self.enabled = bool(self.connection_string)
        self.client = None
        self.message_handlers = {}
        self.fallback_queues = {}
        self.processing_threads = {}
        
        # Queue names for different message types
        self.queue_names = {
            'task_updates': 'task-updates',
            'project_updates': 'project-updates',
            'sharing_notifications': 'sharing-notifications',
            'websocket_messages': 'websocket-messages'
        }
        
        if self.enabled:
            self._initialize_client()
        else:
            self._initialize_fallback_queues()
    
    def _initialize_client(self):
        """Initialize Azure Service Bus client"""
        try:
            from azure.servicebus import ServiceBusClient
            
            self.client = ServiceBusClient.from_connection_string(self.connection_string)
            logger.info("Azure Service Bus client initialized successfully")
            
        except ImportError:
            logger.warning("Azure Service Bus SDK not available, using fallback queues")
            self.enabled = False
            self._initialize_fallback_queues()
        except Exception as e:
            logger.error(f"Failed to initialize Azure Service Bus: {e}")
            self.enabled = False
            self._initialize_fallback_queues()
    
    def _initialize_fallback_queues(self):
        """Initialize in-memory fallback queues"""
        for queue_name in self.queue_names.values():
            self.fallback_queues[queue_name] = []
        logger.info("Fallback in-memory queues initialized")
    
    def is_available(self) -> bool:
        """Check if Azure Service Bus is available"""
        return self.enabled and self.client is not None
    
    async def send_message(self, queue_name: str, message: ServiceBusMessage) -> bool:
        """Send message to Service Bus queue"""
        if not self.is_available():
            return self._fallback_send_message(queue_name, message)
        
        try:
            from azure.servicebus import ServiceBusMessage as AzureMessage
            
            # Create Azure Service Bus message
            azure_message = AzureMessage(
                body=json.dumps(message.to_dict()),
                content_type='application/json',
                correlation_id=message.correlation_id
            )
            
            # Add custom properties
            azure_message.application_properties = {
                'message_type': message.message_type,
                'project_id': message.project_id,
                'user_id': message.user_id,
                'timestamp': message.timestamp
            }
            
            # Send message
            async with self.client.get_queue_sender(queue_name) as sender:
                await sender.send_messages(azure_message)
            
            logger.debug(f"Message sent to queue {queue_name}: {message.message_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message to Azure Service Bus: {e}")
            return self._fallback_send_message(queue_name, message)
    
    def send_task_update(self, project_id: int, task_data: Dict[str, Any], 
                        user_id: int = None) -> bool:
        """Send task update message"""
        message = ServiceBusMessage(
            message_type='task_update',
            data=task_data,
            project_id=project_id,
            user_id=user_id
        )
        
        # Use asyncio to send message
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                self.send_message(self.queue_names['task_updates'], message)
            )
        except RuntimeError:
            # Create new event loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.send_message(self.queue_names['task_updates'], message)
                )
            finally:
                loop.close()
    
    def send_project_update(self, project_id: int, update_data: Dict[str, Any],
                          user_id: int = None) -> bool:
        """Send project update message"""
        message = ServiceBusMessage(
            message_type='project_update',
            data=update_data,
            project_id=project_id,
            user_id=user_id
        )
        
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                self.send_message(self.queue_names['project_updates'], message)
            )
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.send_message(self.queue_names['project_updates'], message)
                )
            finally:
                loop.close()
    
    def send_sharing_notification(self, project_id: int, notification_data: Dict[str, Any],
                                user_id: int = None) -> bool:
        """Send sharing notification message"""
        message = ServiceBusMessage(
            message_type='sharing_notification',
            data=notification_data,
            project_id=project_id,
            user_id=user_id
        )
        
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                self.send_message(self.queue_names['sharing_notifications'], message)
            )
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.send_message(self.queue_names['sharing_notifications'], message)
                )
            finally:
                loop.close()
    
    def send_websocket_message(self, project_id: int, ws_data: Dict[str, Any],
                             user_id: int = None) -> bool:
        """Send WebSocket message for real-time updates"""
        message = ServiceBusMessage(
            message_type='websocket_message',
            data=ws_data,
            project_id=project_id,
            user_id=user_id
        )
        
        return asyncio.run(self.send_message(self.queue_names['websocket_messages'], message))
    
    def register_message_handler(self, queue_name: str, handler: Callable[[ServiceBusMessage], None]):
        """Register message handler for a queue"""
        self.message_handlers[queue_name] = handler
        
        if self.is_available():
            self._start_azure_message_processor(queue_name)
        else:
            self._start_fallback_message_processor(queue_name)
    
    def _start_azure_message_processor(self, queue_name: str):
        """Start Azure Service Bus message processor"""
        def process_messages():
            try:
                with self.client.get_queue_receiver(queue_name) as receiver:
                    for message in receiver:
                        try:
                            # Parse message
                            message_data = json.loads(str(message))
                            service_message = ServiceBusMessage.from_dict(message_data)
                            
                            # Handle message
                            handler = self.message_handlers.get(queue_name)
                            if handler:
                                handler(service_message)
                            
                            # Complete message
                            receiver.complete_message(message)
                            
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                            receiver.abandon_message(message)
                            
            except Exception as e:
                logger.error(f"Error in message processor for {queue_name}: {e}")
        
        # Start processing thread
        thread = threading.Thread(target=process_messages, daemon=True)
        thread.start()
        self.processing_threads[queue_name] = thread
    
    def _start_fallback_message_processor(self, queue_name: str):
        """Start fallback message processor"""
        def process_fallback_messages():
            import time
            while True:
                try:
                    if queue_name in self.fallback_queues and self.fallback_queues[queue_name]:
                        message = self.fallback_queues[queue_name].pop(0)
                        
                        handler = self.message_handlers.get(queue_name)
                        if handler:
                            handler(message)
                    
                    time.sleep(0.1)  # Small delay to prevent busy waiting
                    
                except Exception as e:
                    logger.error(f"Error in fallback processor for {queue_name}: {e}")
                    time.sleep(1)
        
        # Start processing thread
        thread = threading.Thread(target=process_fallback_messages, daemon=True)
        thread.start()
        self.processing_threads[queue_name] = thread
    
    def _fallback_send_message(self, queue_name: str, message: ServiceBusMessage) -> bool:
        """Send message to fallback in-memory queue"""
        try:
            if queue_name not in self.fallback_queues:
                self.fallback_queues[queue_name] = []
            
            self.fallback_queues[queue_name].append(message)
            logger.debug(f"Message added to fallback queue {queue_name}: {message.message_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message to fallback queue: {e}")
            return False
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get service status information"""
        return {
            'enabled': self.enabled,
            'connection_configured': bool(self.connection_string),
            'client_initialized': self.client is not None,
            'active_handlers': list(self.message_handlers.keys()),
            'fallback_queues': {name: len(queue) for name, queue in self.fallback_queues.items()},
            'service_name': 'Azure Service Bus'
        }


class ServiceBusMessageHandlers:
    """Message handlers for different queue types"""
    
    def __init__(self, app=None, signalr_service=None, email_service=None):
        self.app = app
        self.signalr_service = signalr_service
        self.email_service = email_service
    
    def handle_task_update(self, message: ServiceBusMessage):
        """Handle task update messages"""
        try:
            logger.info(f"Processing task update: {message.message_type}")
            
            # Send real-time update via SignalR
            if self.signalr_service:
                self.signalr_service.send_to_group(
                    group_id=str(message.project_id),
                    message={
                        'type': 'task_update',
                        'data': message.data
                    }
                )
            
            # Additional task update processing can be added here
            
        except Exception as e:
            logger.error(f"Error handling task update: {e}")
            raise
    
    def handle_project_update(self, message: ServiceBusMessage):
        """Handle project update messages"""
        try:
            logger.info(f"Processing project update: {message.message_type}")
            
            # Send real-time update via SignalR
            if self.signalr_service:
                self.signalr_service.send_to_group(
                    group_id=str(message.project_id),
                    message={
                        'type': 'project_update',
                        'data': message.data
                    }
                )
            
            # Additional project update processing can be added here
            
        except Exception as e:
            logger.error(f"Error handling project update: {e}")
            raise
    
    def handle_sharing_notification(self, message: ServiceBusMessage):
        """Handle sharing notification messages"""
        try:
            logger.info(f"Processing sharing notification: {message.message_type}")
            
            # Send email notification if email service is available
            if self.email_service:
                notification_data = message.data
                if 'recipient_email' in notification_data:
                    self.email_service.send_notification_email(
                        to_email=notification_data['recipient_email'],
                        notification_type=notification_data.get('notification_type', 'project_shared'),
                        project_name=notification_data.get('project_name', 'Unknown Project'),
                        details=notification_data
                    )
            
            # Send real-time update via SignalR
            if self.signalr_service:
                self.signalr_service.send_to_group(
                    group_id=str(message.project_id),
                    message={
                        'type': 'sharing_notification',
                        'data': message.data
                    }
                )
            
            # Additional sharing notification processing can be added here
            
        except Exception as e:
            logger.error(f"Error handling sharing notification: {e}")
            raise
    
    def handle_websocket_message(self, message: ServiceBusMessage):
        """Handle WebSocket messages for real-time updates"""
        try:
            logger.info(f"Processing WebSocket message: {message.message_type}")
            
            # Send real-time update via SignalR
            if self.signalr_service:
                if message.user_id:
                    self.signalr_service.send_to_user(
                        user_id=str(message.user_id),
                        message={
                            'type': 'websocket_message',
                            'data': message.data
                        }
                    )
                else:
                    self.signalr_service.send_to_group(
                        group_id=str(message.project_id),
                        message={
                            'type': 'websocket_message',
                            'data': message.data
                        }
                    )
            
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            raise


def create_service_bus_service(connection_string: str = None) -> AzureServiceBusService:
    """Create and configure Azure Service Bus Service"""
    return AzureServiceBusService(connection_string)


def setup_message_handlers(service_bus_service: AzureServiceBusService, 
                          app=None, signalr_service=None, email_service=None):
    """Setup message handlers for Azure Service Bus"""
    handlers = ServiceBusMessageHandlers(app, signalr_service, email_service)
    
    # Register handlers for different queue types
    service_bus_service.register_message_handler(
        service_bus_service.queue_names['task_updates'], 
        handlers.handle_task_update
    )
    
    service_bus_service.register_message_handler(
        service_bus_service.queue_names['project_updates'], 
        handlers.handle_project_update
    )
    
    service_bus_service.register_message_handler(
        service_bus_service.queue_names['sharing_notifications'], 
        handlers.handle_sharing_notification
    )
    
    service_bus_service.register_message_handler(
        service_bus_service.queue_names['websocket_messages'], 
        handlers.handle_websocket_message
    )
"""
Azure Services Configuration Module

Manages configuration and initialization of Azure services including:
- Azure SignalR Service
- Azure Communication Services  
- Azure Service Bus
- Azure Key Vault
- Azure Application Insights
"""

import os
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class AzureServiceConfig:
    """Base configuration for Azure services"""
    connection_string: str
    enabled: bool = True
    service_name: str = ""


class AzureServicesManager:
    """Manager for Azure services integration"""
    
    def __init__(self):
        self.is_azure = self._is_azure_environment()
        self.services = {}
        self._initialize_service_configs()
    
    def _is_azure_environment(self) -> bool:
        """Check if running in Azure environment"""
        azure_indicators = [
            'WEBSITE_SITE_NAME',
            'WEBSITE_RESOURCE_GROUP', 
            'APPSETTING_WEBSITE_SITE_NAME'
        ]
        return any(os.environ.get(indicator) for indicator in azure_indicators)
    
    def _initialize_service_configs(self):
        """Initialize configuration for all Azure services"""
        self.services = {
            'signalr': AzureServiceConfig(
                connection_string=os.environ.get('AZURE_SIGNALR_CONNECTION_STRING', ''),
                enabled=bool(os.environ.get('AZURE_SIGNALR_CONNECTION_STRING')),
                service_name='Azure SignalR Service'
            ),
            'communication': AzureServiceConfig(
                connection_string=os.environ.get('AZURE_COMMUNICATION_CONNECTION_STRING', ''),
                enabled=bool(os.environ.get('AZURE_COMMUNICATION_CONNECTION_STRING')),
                service_name='Azure Communication Services'
            ),
            'service_bus': AzureServiceConfig(
                connection_string=os.environ.get('AZURE_SERVICE_BUS_CONNECTION_STRING', ''),
                enabled=bool(os.environ.get('AZURE_SERVICE_BUS_CONNECTION_STRING')),
                service_name='Azure Service Bus'
            ),
            'key_vault': AzureServiceConfig(
                connection_string=os.environ.get('AZURE_KEY_VAULT_URL', ''),
                enabled=bool(os.environ.get('AZURE_KEY_VAULT_URL')),
                service_name='Azure Key Vault'
            ),
            'app_insights': AzureServiceConfig(
                connection_string=os.environ.get('APPLICATIONINSIGHTS_CONNECTION_STRING', ''),
                enabled=bool(os.environ.get('APPLICATIONINSIGHTS_CONNECTION_STRING')),
                service_name='Azure Application Insights'
            )
        }
    
    def get_service_config(self, service_name: str) -> Optional[AzureServiceConfig]:
        """Get configuration for a specific service"""
        return self.services.get(service_name)
    
    def is_service_enabled(self, service_name: str) -> bool:
        """Check if a service is enabled and configured"""
        config = self.get_service_config(service_name)
        return config and config.enabled and config.connection_string
    
    def get_enabled_services(self) -> List[str]:
        """Get list of enabled services"""
        return [name for name, config in self.services.items() 
                if config.enabled and config.connection_string]
    
    def validate_services(self) -> Dict[str, str]:
        """Validate all service configurations"""
        validation_results = {}
        
        for service_name, config in self.services.items():
            if not config.enabled:
                validation_results[service_name] = 'disabled'
                continue
                
            if not config.connection_string:
                validation_results[service_name] = 'missing_connection_string'
                continue
            
            # Service-specific validation
            if service_name == 'signalr':
                validation_results[service_name] = self._validate_signalr_config(config.connection_string)
            elif service_name == 'communication':
                validation_results[service_name] = self._validate_communication_config(config.connection_string)
            elif service_name == 'service_bus':
                validation_results[service_name] = self._validate_service_bus_config(config.connection_string)
            elif service_name == 'key_vault':
                validation_results[service_name] = self._validate_key_vault_config(config.connection_string)
            elif service_name == 'app_insights':
                validation_results[service_name] = self._validate_app_insights_config(config.connection_string)
            else:
                validation_results[service_name] = 'valid'
        
        return validation_results
    
    def _validate_signalr_config(self, connection_string: str) -> str:
        """Validate Azure SignalR configuration"""
        if not connection_string.startswith('Endpoint=https://'):
            return 'invalid_format'
        if 'AccessKey=' not in connection_string:
            return 'missing_access_key'
        return 'valid'
    
    def _validate_communication_config(self, connection_string: str) -> str:
        """Validate Azure Communication Services configuration"""
        if not connection_string.startswith('endpoint=https://'):
            return 'invalid_format'
        if 'accesskey=' not in connection_string.lower():
            return 'missing_access_key'
        return 'valid'
    
    def _validate_service_bus_config(self, connection_string: str) -> str:
        """Validate Azure Service Bus configuration"""
        if not connection_string.startswith('Endpoint=sb://'):
            return 'invalid_format'
        if 'SharedAccessKeyName=' not in connection_string:
            return 'missing_key_name'
        if 'SharedAccessKey=' not in connection_string:
            return 'missing_access_key'
        return 'valid'
    
    def _validate_key_vault_config(self, vault_url: str) -> str:
        """Validate Azure Key Vault configuration"""
        if not vault_url.startswith('https://'):
            return 'invalid_format'
        if '.vault.azure.net' not in vault_url:
            return 'invalid_vault_url'
        return 'valid'
    
    def _validate_app_insights_config(self, connection_string: str) -> str:
        """Validate Azure Application Insights configuration"""
        if not connection_string.startswith('InstrumentationKey='):
            return 'invalid_format'
        return 'valid'


def configure_flask_app_with_azure_services(app):
    """Configure Flask app with Azure services"""
    manager = create_azure_services_manager()
    
    # Store manager in app context
    app.azure_services_manager = manager
    
    # Configure each enabled service
    enabled_services = manager.get_enabled_services()
    
    if 'signalr' in enabled_services:
        signalr_config = manager.get_service_config('signalr')
        app.config['AZURE_SIGNALR_CONFIG'] = signalr_config
        logger.info("Azure SignalR Service configured")
    
    if 'communication' in enabled_services:
        comm_config = manager.get_service_config('communication')
        app.config['AZURE_COMMUNICATION_CONFIG'] = comm_config
        logger.info("Azure Communication Services configured")
    
    if 'service_bus' in enabled_services:
        bus_config = manager.get_service_config('service_bus')
        app.config['AZURE_SERVICE_BUS_CONFIG'] = bus_config
        logger.info("Azure Service Bus configured")
    
    if 'key_vault' in enabled_services:
        kv_config = manager.get_service_config('key_vault')
        app.config['AZURE_KEY_VAULT_CONFIG'] = kv_config
        logger.info("Azure Key Vault configured")
    
    if 'app_insights' in enabled_services:
        ai_config = manager.get_service_config('app_insights')
        app.config['AZURE_APP_INSIGHTS_CONFIG'] = ai_config
        logger.info("Azure Application Insights configured")
    
    logger.info(f"Azure services configured: {enabled_services}")
    return app


def create_azure_services_manager() -> AzureServicesManager:
    """Create and configure Azure services manager"""
    return AzureServicesManager()


def get_azure_services_status() -> Dict[str, Any]:
    """Get status of all Azure services"""
    manager = create_azure_services_manager()
    
    return {
        'is_azure_environment': manager.is_azure,
        'enabled_services': manager.get_enabled_services(),
        'service_validation': manager.validate_services(),
        'overall_status': 'healthy' if manager.get_enabled_services() else 'no_services_configured'
    }
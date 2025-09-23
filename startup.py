"""
Azure App Service Startup Script

This script handles initialization and startup tasks for the project sharing
application when deployed to Azure App Service.
"""

import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_azure_environment():
    """Setup Azure-specific environment configuration"""
    logger.info("Setting up Azure environment...")
    
    # Set Python path
    if '/home/site/wwwroot' not in sys.path:
        sys.path.insert(0, '/home/site/wwwroot')
    
    # Set environment variables for Azure App Service
    os.environ.setdefault('PYTHONPATH', '/home/site/wwwroot')
    
    # Configure for production
    os.environ.setdefault('FLASK_ENV', 'production')
    os.environ.setdefault('FLASK_DEBUG', 'False')
    
    # Ensure static directory exists and is accessible
    static_dir = '/home/site/wwwroot/static'
    if os.path.exists(static_dir):
        logger.info(f"Static directory found: {static_dir}")
        # List some static files for debugging
        try:
            for root, dirs, files in os.walk(static_dir):
                if files:
                    logger.info(f"Static files in {root}: {files[:5]}")  # Show first 5 files
                    break
        except Exception as e:
            logger.warning(f"Could not list static files: {e}")
    else:
        logger.warning(f"Static directory not found: {static_dir}")
    
    logger.info("Azure environment setup completed")


def validate_configuration():
    """Validate required configuration for Azure deployment"""
    logger.info("Validating configuration...")
    
    required_vars = ['SECRET_KEY', 'DATABASE_URL']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        return False
    
    # Validate database URL format
    database_url = os.environ.get('DATABASE_URL', '')
    if not any(db_type in database_url.lower() for db_type in ['mssql', 'postgresql', 'sqlite']):
        logger.error("Invalid DATABASE_URL format")
        return False
    
    logger.info("Configuration validation passed")
    return True


def initialize_database():
    """Initialize database tables if needed"""
    logger.info("Initializing database...")
    
    try:
        # Import after environment setup
        from app import app, db
        
        with app.app_context():
            # Create tables if they don't exist
            db.create_all()
            logger.info("Database tables created/verified successfully")
            
            # Run any pending migrations
            try:
                from migrations.azure_production_migration import run_production_migration
                migration_success = run_production_migration()
                if migration_success:
                    logger.info("Azure production migration completed successfully")
                else:
                    logger.warning("Azure production migration completed with warnings")
            except ImportError:
                logger.info("No Azure migration script found, skipping")
            except Exception as e:
                logger.warning(f"Azure migration failed: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


def setup_azure_services():
    """Setup and validate Azure services"""
    logger.info("Setting up Azure services...")
    
    try:
        from services.azure_services_config import get_azure_services_status
        
        status = get_azure_services_status()
        enabled_services = status.get('enabled_services', [])
        
        logger.info(f"Azure services status: {status['is_azure_environment']}")
        logger.info(f"Enabled services: {enabled_services}")
        
        if len(enabled_services) > 0:
            logger.info("Azure services configured successfully")
        else:
            logger.info("No Azure services configured, using fallback implementations")
        
        return True
        
    except Exception as e:
        logger.error(f"Azure services setup failed: {e}")
        return False


def run_health_checks():
    """Run startup health checks"""
    logger.info("Running startup health checks...")
    
    try:
        # Simple health check - just verify the app can be imported
        from app import app
        logger.info("Health check completed. App imported successfully.")
        
        # Check static files
        static_files_to_check = [
            'static/css/style.css',
            'static/js/main.js',
            'static/js/websocket-client.js'
        ]
        
        for static_file in static_files_to_check:
            if os.path.exists(static_file):
                logger.info(f"Static file found: {static_file}")
            else:
                logger.warning(f"Static file missing: {static_file}")
        
        return True
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False


def main():
    """Main startup function"""
    logger.info("=" * 50)
    logger.info("Starting Azure App Service initialization")
    logger.info(f"Timestamp: {datetime.utcnow().isoformat()}")
    logger.info("=" * 50)
    
    # Setup Azure environment
    setup_azure_environment()
    
    # Validate configuration
    if not validate_configuration():
        logger.error("Configuration validation failed. Exiting.")
        sys.exit(1)
    
    # Initialize database
    if not initialize_database():
        logger.error("Database initialization failed. Exiting.")
        sys.exit(1)
    
    # Setup Azure services
    if not setup_azure_services():
        logger.warning("Azure services setup had issues, but continuing with fallbacks")
    
    # Run health checks
    if not run_health_checks():
        logger.warning("Health checks indicate potential issues, but continuing startup")
    
    logger.info("=" * 50)
    logger.info("Azure App Service initialization completed successfully")
    logger.info("=" * 50)
    
    # Import and run the Flask application
    try:
        from app import app
        
        # Get port from environment (Azure App Service sets this)
        port = int(os.environ.get('PORT', 8000))
        
        logger.info(f"Starting Flask application on port {port}")
        
        # Run Flask application
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False
        )
        
    except Exception as e:
        logger.error(f"Failed to start Flask application: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
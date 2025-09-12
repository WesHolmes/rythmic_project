#!/usr/bin/env python3
"""
Startup script for Azure App Service deployment
"""
import os
import logging
from app import app, db
from database_config import get_database_info

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_database():
    """Initialize database with proper error handling"""
    try:
        # Log database configuration
        db_info = get_database_info()
        logger.info(f"Database configuration: {db_info}")
        
        # Check if database connection is valid
        if not db_info.get('is_valid'):
            error_msg = db_info.get('error', 'Unknown database error')
            logger.error(f"Database connection failed: {error_msg}")
            
            # In Azure, if PostgreSQL fails, we should not continue with SQLite
            if db_info.get('is_azure') and not db_info.get('is_postgresql'):
                logger.error("SQLite fallback detected in Azure environment - this will not persist data!")
            
            raise Exception(f"Database connection failed: {error_msg}")
        
        # Create database tables
        with app.app_context():
            db.create_all()
            logger.info("Database tables created successfully")
            
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

if __name__ == "__main__":
    try:
        # Initialize database
        initialize_database()
        
        # Azure App Service will set the PORT environment variable
        port = int(os.environ.get('PORT', 8000))
        logger.info(f"Starting Flask app on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        # In production, we might want to exit gracefully
        raise
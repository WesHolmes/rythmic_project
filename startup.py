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
        # Try to get database info if available
        try:
            db_info = get_database_info()
            logger.info(f"Database configuration: {db_info}")
        except Exception as e:
            logger.warning(f"Could not get database info: {e}")
        
        # Create database tables
        with app.app_context():
            db.create_all()
            logger.info("Database tables created successfully")
            
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        # Don't raise the exception - let the app start anyway
        logger.info("Continuing without database initialization - will retry on first request")

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
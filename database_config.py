"""
Database configuration module for Azure-compatible database setup.
Handles environment detection and database URL generation with fallback support.
"""

import os
import logging
from typing import Optional, Tuple
from urllib.parse import urlparse
import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def is_azure_environment() -> bool:
    """
    Detect if the application is running in Azure App Service.
    
    Returns:
        bool: True if running in Azure, False otherwise
    """
    # Azure App Service sets specific environment variables
    azure_indicators = [
        'WEBSITE_SITE_NAME',  # Azure App Service
        'WEBSITE_RESOURCE_GROUP',  # Azure App Service
        'APPSETTING_WEBSITE_SITE_NAME',  # Alternative Azure indicator
    ]
    
    return any(os.environ.get(indicator) for indicator in azure_indicators)


def get_postgresql_url() -> Optional[str]:
    """
    Generate PostgreSQL connection URL from environment variables.
    
    Returns:
        str: PostgreSQL connection URL if all required variables are present, None otherwise
    """
    # Check for complete DATABASE_URL first
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Fix postgres:// to postgresql:// for SQLAlchemy compatibility
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        return database_url
    
    # Build from individual components
    host = os.environ.get('POSTGRES_HOST')
    user = os.environ.get('POSTGRES_USER')
    password = os.environ.get('POSTGRES_PASSWORD')
    database = os.environ.get('POSTGRES_DB')
    port = os.environ.get('POSTGRES_PORT', '5432')
    
    if all([host, user, password, database]):
        # Ensure SSL for Azure PostgreSQL
        ssl_mode = 'require' if is_azure_environment() else 'prefer'
        return f"postgresql://{user}:{password}@{host}:{port}/{database}?sslmode={ssl_mode}"
    
    return None


def get_sqlite_url() -> str:
    """
    Generate SQLite connection URL with proper path handling.
    
    Returns:
        str: SQLite connection URL
    """
    # Default SQLite path
    sqlite_path = os.environ.get('SQLITE_PATH', 'instance/rhythmic.db')
    
    # Convert relative path to absolute path if needed
    if not os.path.isabs(sqlite_path):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sqlite_path = os.path.join(base_dir, sqlite_path)
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
    
    return f"sqlite:///{sqlite_path}"


def validate_connection(database_url: str, timeout: int = 10) -> Tuple[bool, Optional[str]]:
    """
    Validate database connection by attempting to connect and execute a simple query.
    
    Args:
        database_url: Database connection URL to validate
        timeout: Connection timeout in seconds
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    try:
        # Create engine with timeout
        engine = create_engine(
            database_url,
            connect_args={'timeout': timeout} if 'sqlite' in database_url else {},
            pool_timeout=timeout,
            pool_recycle=3600  # Recycle connections every hour
        )
        
        # Test connection
        with engine.connect() as connection:
            # Execute a simple query to verify the connection works
            if 'postgresql' in database_url:
                connection.execute(text("SELECT 1"))
            else:  # SQLite
                connection.execute(text("SELECT 1"))
        
        logger.info(f"Database connection validated successfully: {_sanitize_url(database_url)}")
        return True, None
        
    except OperationalError as e:
        error_msg = f"Database connection failed: {str(e)}"
        logger.error(f"{error_msg} for URL: {_sanitize_url(database_url)}")
        return False, error_msg
        
    except SQLAlchemyError as e:
        error_msg = f"Database error: {str(e)}"
        logger.error(f"{error_msg} for URL: {_sanitize_url(database_url)}")
        return False, error_msg
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"{error_msg} for URL: {_sanitize_url(database_url)}")
        return False, error_msg


def get_database_url() -> str:
    """
    Get the appropriate database URL based on environment and configuration.
    
    Priority order:
    1. PostgreSQL (if configured and in Azure or explicitly requested)
    2. SQLite (fallback for local development)
    
    Returns:
        str: Database connection URL
    """
    # Try PostgreSQL first if we're in Azure or have PostgreSQL config
    postgresql_url = get_postgresql_url()
    
    if postgresql_url:
        is_valid, error = validate_connection(postgresql_url)
        if is_valid:
            logger.info("Using PostgreSQL database")
            return postgresql_url
        else:
            logger.warning(f"PostgreSQL connection failed: {error}")
            
            # In Azure, we should not fall back to SQLite as it won't persist
            if is_azure_environment():
                logger.error("PostgreSQL connection failed in Azure environment. SQLite fallback not recommended.")
                # Still return PostgreSQL URL to let the application handle the error appropriately
                return postgresql_url
    
    # Fallback to SQLite
    sqlite_url = get_sqlite_url()
    
    if is_azure_environment():
        logger.warning("Using SQLite in Azure environment - data will not persist across restarts!")
    else:
        logger.info("Using SQLite database for local development")
    
    return sqlite_url


def get_database_info() -> dict:
    """
    Get information about the current database configuration.
    
    Returns:
        dict: Database configuration information
    """
    database_url = get_database_url()
    parsed_url = urlparse(database_url)
    
    info = {
        'url': _sanitize_url(database_url),
        'scheme': parsed_url.scheme,
        'is_azure': is_azure_environment(),
        'is_postgresql': 'postgresql' in database_url,
        'is_sqlite': 'sqlite' in database_url,
    }
    
    # Add connection validation
    is_valid, error = validate_connection(database_url)
    info['is_valid'] = is_valid
    info['error'] = error
    
    return info


def _sanitize_url(url: str) -> str:
    """
    Sanitize database URL by removing sensitive information for logging.
    
    Args:
        url: Database URL to sanitize
        
    Returns:
        str: Sanitized URL with password removed
    """
    try:
        parsed = urlparse(url)
        if parsed.password:
            # Replace password with asterisks
            sanitized = url.replace(parsed.password, '***')
            return sanitized
        return url
    except Exception:
        return url


# Configuration constants
DEFAULT_SQLITE_PATH = 'instance/rhythmic.db'
DEFAULT_POSTGRES_PORT = '5432'
CONNECTION_TIMEOUT = 10
POOL_RECYCLE_TIME = 3600  # 1 hour
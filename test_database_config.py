"""
Test script for database configuration module.
"""

import os
import tempfile
from database_config import (
    is_azure_environment,
    get_postgresql_url,
    get_sqlite_url,
    get_database_url,
    get_database_info,
    validate_connection
)


def test_environment_detection():
    """Test Azure environment detection."""
    print("Testing environment detection...")
    
    # Test local environment (should be False)
    print(f"Current environment is Azure: {is_azure_environment()}")
    
    # Test with Azure environment variable
    os.environ['WEBSITE_SITE_NAME'] = 'test-app'
    print(f"With WEBSITE_SITE_NAME set: {is_azure_environment()}")
    
    # Clean up
    if 'WEBSITE_SITE_NAME' in os.environ:
        del os.environ['WEBSITE_SITE_NAME']


def test_postgresql_url_generation():
    """Test PostgreSQL URL generation."""
    print("\nTesting PostgreSQL URL generation...")
    
    # Test with no environment variables
    print(f"No PostgreSQL config: {get_postgresql_url()}")
    
    # Test with DATABASE_URL
    os.environ['DATABASE_URL'] = 'postgres://user:pass@localhost:5432/testdb'
    print(f"With DATABASE_URL: {get_postgresql_url()}")
    
    # Clean up and test individual variables
    del os.environ['DATABASE_URL']
    os.environ.update({
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_USER': 'testuser',
        'POSTGRES_PASSWORD': 'testpass',
        'POSTGRES_DB': 'testdb'
    })
    print(f"With individual vars: {get_postgresql_url()}")
    
    # Clean up
    for key in ['POSTGRES_HOST', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB']:
        if key in os.environ:
            del os.environ[key]


def test_sqlite_url_generation():
    """Test SQLite URL generation."""
    print("\nTesting SQLite URL generation...")
    
    # Test default path
    print(f"Default SQLite URL: {get_sqlite_url()}")
    
    # Test custom path
    with tempfile.TemporaryDirectory() as temp_dir:
        custom_path = os.path.join(temp_dir, 'custom.db')
        os.environ['SQLITE_PATH'] = custom_path
        print(f"Custom SQLite URL: {get_sqlite_url()}")
        del os.environ['SQLITE_PATH']


def test_database_url_selection():
    """Test database URL selection logic."""
    print("\nTesting database URL selection...")
    
    # Test default (should be SQLite)
    url = get_database_url()
    print(f"Default database URL: {url}")
    
    # Test with PostgreSQL config
    os.environ.update({
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_USER': 'testuser',
        'POSTGRES_PASSWORD': 'testpass',
        'POSTGRES_DB': 'testdb'
    })
    url = get_database_url()
    print(f"With PostgreSQL config: {url}")
    
    # Clean up
    for key in ['POSTGRES_HOST', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB']:
        if key in os.environ:
            del os.environ[key]


def test_database_info():
    """Test database info function."""
    print("\nTesting database info...")
    
    info = get_database_info()
    print("Database info:")
    for key, value in info.items():
        print(f"  {key}: {value}")


def test_connection_validation():
    """Test connection validation with SQLite."""
    print("\nTesting connection validation...")
    
    # Test with SQLite (should work)
    sqlite_url = get_sqlite_url()
    is_valid, error = validate_connection(sqlite_url)
    print(f"SQLite connection valid: {is_valid}")
    if error:
        print(f"SQLite error: {error}")
    
    # Test with invalid URL
    is_valid, error = validate_connection("sqlite:///nonexistent/path/db.sqlite")
    print(f"Invalid SQLite connection valid: {is_valid}")
    if error:
        print(f"Invalid SQLite error: {error}")


if __name__ == "__main__":
    print("Database Configuration Module Tests")
    print("=" * 40)
    
    test_environment_detection()
    test_postgresql_url_generation()
    test_sqlite_url_generation()
    test_database_url_selection()
    test_database_info()
    test_connection_validation()
    
    print("\nTests completed!")
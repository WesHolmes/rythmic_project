#!/usr/bin/env python3
"""
Test script to verify database connection
"""
import os
from database_config import get_database_info, get_database_url, validate_connection

def test_database_connection():
    """Test database connection and print results"""
    print("Testing database connection...")
    print("-" * 50)
    
    # Get database info
    db_info = get_database_info()
    print(f"Database URL: {db_info['url']}")
    print(f"Database Type: {db_info['scheme']}")
    print(f"Is Azure Environment: {db_info['is_azure']}")
    print(f"Is Azure SQL: {db_info['is_azure_sql']}")
    print(f"Is PostgreSQL: {db_info['is_postgresql']}")
    print(f"Is SQLite: {db_info['is_sqlite']}")
    print(f"Connection Valid: {db_info['is_valid']}")
    
    if db_info['error']:
        print(f"Error: {db_info['error']}")
    
    print("-" * 50)
    
    # Test connection directly
    database_url = get_database_url()
    is_valid, error = validate_connection(database_url)
    
    if is_valid:
        print("✅ Database connection successful!")
    else:
        print(f"❌ Database connection failed: {error}")
    
    return is_valid

if __name__ == "__main__":
    test_database_connection()
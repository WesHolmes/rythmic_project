#!/usr/bin/env python3
"""
Startup script for Azure App Service deployment
"""
import os
import sys

# Configure for Azure
try:
    from azure_config import configure_for_azure
    configure_for_azure()
except ImportError:
    pass

# Import the Flask app
from app import app, db

# Create database tables if they don't exist
with app.app_context():
    try:
        db.create_all()
        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {e}")

if __name__ == "__main__":
    # Azure App Service will set the PORT environment variable
    port = int(os.environ.get('PORT', 8000))
    print(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
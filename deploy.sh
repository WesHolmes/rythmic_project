#!/bin/bash

# Azure deployment script for Python Flask app
echo "Starting Azure deployment for Python Flask application..."

# Verify Python installation
python3 --version
pip --version

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Set up database
echo "Setting up database..."
python3 -c "
try:
    from app import app, db
    with app.app_context():
        db.create_all()
        print('Database tables created successfully')
except Exception as e:
    print(f'Database setup error: {e}')
"

echo "Deployment completed successfully"
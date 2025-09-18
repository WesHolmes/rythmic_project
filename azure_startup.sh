#!/bin/bash

echo "Installing ODBC drivers for Azure SQL Database..."

# Update package lists
apt-get update

# Install prerequisites
ACCEPT_EULA=Y apt-get install -y curl gnupg

# Add Microsoft repository
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list

# Update and install ODBC driver
apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev

echo "ODBC drivers installed successfully"

# Start the application
echo "Starting Gunicorn server..."
exec gunicorn --bind=0.0.0.0:$PORT --timeout 600 --worker-class gevent --workers 1 wsgi:application
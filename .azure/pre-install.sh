#!/bin/bash

# Pre-install script for Azure App Service to install ODBC drivers
echo "Installing ODBC drivers for pyodbc..."

# Install system dependencies for pyodbc
apt-get update
apt-get install -y curl gnupg

# Add Microsoft repository
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list

# Update and install ODBC driver
apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev

echo "ODBC drivers installed successfully"
#!/bin/bash
# Startup script to install ODBC drivers on Azure Functions Linux
# Place this in: azure_functions/startup.sh

echo "=========================================="
echo "Installing ODBC Drivers for SQL Server"
echo "=========================================="

# Update package list
echo "Updating package lists..."
apt-get update -qq

# Install prerequisites
echo "Installing prerequisites..."
apt-get install -y -qq curl gnupg2 apt-transport-https

# Add Microsoft repository
echo "Adding Microsoft repository..."
curl -sSL https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl -sSL https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list

# Update after adding repository
echo "Updating package lists with Microsoft repository..."
apt-get update -qq

# Install ODBC Driver 18 for SQL Server
echo "Installing ODBC Driver 18..."
ACCEPT_EULA=Y apt-get install -y -qq msodbcsql18

# Install unixODBC development files
echo "Installing unixODBC..."
apt-get install -y -qq unixodbc-dev

# Verify installation
echo "Verifying ODBC driver installation..."
if odbcinst -q -d -n "ODBC Driver 18 for SQL Server" > /dev/null 2>&1; then
    echo "✅ ODBC Driver 18 for SQL Server installed successfully"
else
    echo "❌ ODBC Driver installation failed"
    exit 1
fi

echo "=========================================="
echo "ODBC Driver Installation Complete"
echo "=========================================="
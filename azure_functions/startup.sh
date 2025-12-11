#!/bin/bash
# Startup script to install ODBC drivers on Azure Functions Linux
# Place this in: azure_functions/startup.sh

echo "Installing ODBC drivers for SQL Server..."

# Install required system packages
apt-get update
apt-get install -y curl gnupg2

# Add Microsoft repository
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list

# Install ODBC driver
apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql18

# Install unixODBC
apt-get install -y unixodbc-dev

echo "ODBC drivers installed successfully"
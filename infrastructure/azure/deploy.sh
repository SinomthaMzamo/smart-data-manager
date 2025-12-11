#!/bin/bash
# Azure ETL Deployment Script
# Place this in: infrastructure/azure/deploy.sh

set -e  # Exit on error

# ============================================
# CONFIGURATION - Edit these values
# ============================================
RESOURCE_GROUP="rg-smart-data-manager"
LOCATION="southafricanorth"  # Or your preferred Azure region
ENVIRONMENT="dev"

# If you already have SQL Server/Database, provide names here:
EXISTING_SQL_SERVER="smart-data-manager.database.windows.net"  # Leave as-is to create new
EXISTING_DATABASE="sdm_db"  # Your existing database name

# SQL Admin credentials (only needed if creating new server)
SQL_ADMIN_LOGIN="sdm-admin"

# ============================================
# SCRIPT START
# ============================================
echo "============================================"
echo "Azure ETL Infrastructure Deployment"
echo "============================================"
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found. Install it:"
    echo "   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
    exit 1
fi

# Check if logged in
echo "🔐 Checking Azure login status..."
az account show > /dev/null 2>&1 || {
    echo "Not logged in. Please login..."
    az login
}

SUBSCRIPTION=$(az account show --query name -o tsv)
echo "✅ Logged in to subscription: $SUBSCRIPTION"
echo ""

# Prompt for SQL password
echo "✅ Using existing SQL Server: $EXISTING_SQL_SERVER"
echo "📝 Enter SQL Server admin password for existing server:"
read -s SQL_ADMIN_PASSWORD
export SQL_ADMIN_PASSWORD
echo ""

# Create resource group if it doesn't exist
echo "📦 Creating resource group: $RESOURCE_GROUP in $LOCATION..."
az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION \
    --output table
echo ""

# Deploy Bicep template
echo "🚀 Deploying infrastructure (this may take 3-5 minutes)..."
DEPLOYMENT_OUTPUT=$(az deployment group create \
    --resource-group $RESOURCE_GROUP \
    --template-file main.bicep \
    --parameters \
        environment=$ENVIRONMENT \
        location=$LOCATION \
        sqlAdminLogin=$SQL_ADMIN_LOGIN \
        sqlAdminPassword=$SQL_ADMIN_PASSWORD \
        existingSqlServerName="$EXISTING_SQL_SERVER" \
        existingDatabaseName="$EXISTING_DATABASE" \
    --query 'properties.outputs' \
    --output json)

# Extract outputs
FUNCTION_APP_NAME=$(echo $DEPLOYMENT_OUTPUT | jq -r '.functionAppName.value')
SQL_SERVER_FQDN=$(echo $DEPLOYMENT_OUTPUT | jq -r '.sqlServerFqdn.value')
DATABASE_NAME=$(echo $DEPLOYMENT_OUTPUT | jq -r '.databaseName.value')
STORAGE_ACCOUNT=$(echo $DEPLOYMENT_OUTPUT | jq -r '.storageAccountName.value')

echo ""
echo "✅ Infrastructure deployed successfully!"
echo ""
echo "📊 Deployment Details:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Function App: $FUNCTION_APP_NAME"
echo "  SQL Server: $SQL_SERVER_FQDN"
echo "  Database: $DATABASE_NAME"
echo "  Storage Account: $STORAGE_ACCOUNT"
echo ""

# Now deploy the function code
echo "============================================"
echo "Deploying Function Code"
echo "============================================"
echo ""

# Go to project root
cd ../../

# Create temporary deployment directory
DEPLOY_DIR=".azure_deploy"
rm -rf $DEPLOY_DIR
mkdir -p $DEPLOY_DIR

echo "📦 Preparing function package..."

# Copy Azure Functions structure
cp -r azure_functions/* $DEPLOY_DIR/

# Copy your ETL package (the important part!)
cp -r smart_data_manager_package $DEPLOY_DIR/

# Ensure requirements.txt exists in deploy directory
if [ ! -f "$DEPLOY_DIR/requirements.txt" ]; then
    cat > $DEPLOY_DIR/requirements.txt << EOF
pandas==2.2.2
SQLAlchemy==2.0.30
pyodbc>=5.1.0
azure-functions
EOF
fi

# Create .funcignore to exclude unnecessary files
cat > $DEPLOY_DIR/.funcignore << EOF
.git*
.vscode
__pycache__
*.pyc
.env
local.settings.json
.venv
venv
EOF

# Create deployment package
echo "📦 Creating deployment package..."
cd $DEPLOY_DIR
zip -r ../function_app.zip . -q
cd ..

# Deploy using zip deployment (this works for Linux Python functions)
echo "🚀 Deploying to Azure Function App (this may take 2-3 minutes)..."
az functionapp deployment source config-zip \
    --resource-group $RESOURCE_GROUP \
    --name $FUNCTION_APP_NAME \
    --src function_app.zip \
    --build-remote true

# Cleanup
rm -rf $DEPLOY_DIR
rm function_app.zip

echo ""
echo "============================================"
echo "✅ Deployment Complete!"
echo "============================================"
echo ""
echo "🎯 Your ETL is now running on Azure!"
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Monitor deployment logs:"
echo "   az webapp log tail --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP"
echo ""
echo "2. Test the function:"
echo "   # Get the function key"
echo "   FUNCTION_KEY=\$(az functionapp function keys list \\"
echo "     --resource-group $RESOURCE_GROUP \\"
echo "     --name $FUNCTION_APP_NAME \\"
echo "     --function-name etl_function \\"
echo "     --query default -o tsv)"
echo ""
echo "   # Trigger the function"
echo "   curl -X POST \"https://${FUNCTION_APP_NAME}.azurewebsites.net/api/etl_function?code=\$FUNCTION_KEY\""
echo ""
echo "3. View in Azure Portal:"
echo "   https://portal.azure.com/#resource/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$FUNCTION_APP_NAME"
echo ""
echo "4. Check logs in Application Insights"
echo ""
echo "⏰ Schedule: Runs daily at 4:00 AM UTC"
echo ""
echo "💡 To update code, just run this script again!"
echo ""
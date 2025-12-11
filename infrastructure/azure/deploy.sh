#!/bin/bash
# Updated Azure ETL Deployment Script with ODBC Driver Support
# Place this in: infrastructure/azure/deploy.sh

set -e  # Exit on error

# ============================================
# CONFIGURATION
# ============================================
RESOURCE_GROUP="rg-smart-data-manager"
LOCATION="southafricanorth"
ENVIRONMENT="dev"

# Existing SQL Server details (WITHOUT the .database.windows.net suffix)
EXISTING_SQL_SERVER="smart-data-manager"
EXISTING_DATABASE="sdm_db"
SQL_ADMIN_LOGIN="sdm-admin"

# ============================================
# COLOR OUTPUT
# ============================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${YELLOW}ℹ️  $1${NC}"; }
print_section() { echo -e "\n${GREEN}========================================${NC}"; echo -e "${GREEN}$1${NC}"; echo -e "${GREEN}========================================${NC}\n"; }

# ============================================
# ERROR HANDLING
# ============================================
cleanup() {
    if [ -d "$DEPLOY_DIR" ]; then
        rm -rf "$DEPLOY_DIR"
    fi
    if [ -f "function_app.zip" ]; then
        rm function_app.zip
    fi
}
trap cleanup EXIT
trap 'print_error "Deployment failed at line $LINENO"' ERR

# ============================================
# PREFLIGHT CHECKS
# ============================================
print_section "Preflight Checks"

if ! command -v az &> /dev/null; then
    print_error "Azure CLI not found"
    exit 1
fi
print_success "Azure CLI found"

echo "🔐 Checking Azure login status..."
if ! az account show > /dev/null 2>&1; then
    print_info "Not logged in. Please login..."
    az login
fi

SUBSCRIPTION=$(az account show --query name -o tsv)
print_success "Logged in to subscription: $SUBSCRIPTION"

if ! command -v jq &> /dev/null; then
    print_error "jq is required but not installed"
    exit 1
fi
print_success "jq found"

if [ ! -d "../../azure_functions" ]; then
    print_error "azure_functions directory not found"
    exit 1
fi
print_success "azure_functions directory found"

# ============================================
# GET SQL PASSWORD
# ============================================
print_section "Database Configuration"
print_info "Using existing SQL Server: ${EXISTING_SQL_SERVER}.database.windows.net"
echo "📝 Enter SQL Server admin password:"
read -s SQL_ADMIN_PASSWORD
export SQL_ADMIN_PASSWORD
echo ""

# ============================================
# CREATE RESOURCE GROUP
# ============================================
print_section "Creating Resource Group"
az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION \
    --output table
print_success "Resource group ready"

# ============================================
# DEPLOY INFRASTRUCTURE
# ============================================
print_section "Deploying Infrastructure"
print_info "This may take 3-5 minutes..."

DEPLOYMENT_OUTPUT=$(az deployment group create \
    --resource-group $RESOURCE_GROUP \
    --template-file main.bicep \
    --parameters \
        environment=$ENVIRONMENT \
        location=$LOCATION \
        sqlAdminLogin=$SQL_ADMIN_LOGIN \
        sqlAdminPassword="$SQL_ADMIN_PASSWORD" \
        existingSqlServerName="$EXISTING_SQL_SERVER" \
        existingDatabaseName="$EXISTING_DATABASE" \
    --query 'properties.outputs' \
    --output json)

FUNCTION_APP_NAME=$(echo $DEPLOYMENT_OUTPUT | jq -r '.functionAppName.value')
SQL_SERVER_FQDN=$(echo $DEPLOYMENT_OUTPUT | jq -r '.sqlServerFqdn.value')
DATABASE_NAME=$(echo $DEPLOYMENT_OUTPUT | jq -r '.databaseName.value')
STORAGE_ACCOUNT=$(echo $DEPLOYMENT_OUTPUT | jq -r '.storageAccountName.value')

if [ -z "$FUNCTION_APP_NAME" ] || [ "$FUNCTION_APP_NAME" == "null" ]; then
    print_error "Deployment failed - no function app name returned"
    exit 1
fi

print_success "Infrastructure deployed!"
echo ""
echo "📊 Deployment Details:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Function App: $FUNCTION_APP_NAME"
echo "  SQL Server: $SQL_SERVER_FQDN"
echo "  Database: $DATABASE_NAME"
echo "  Storage Account: $STORAGE_ACCOUNT"
echo ""

# ============================================
# PREPARE FUNCTION CODE
# ============================================
print_section "Preparing Function Code"

cd ../../

DEPLOY_DIR=".azure_deploy"
rm -rf $DEPLOY_DIR
mkdir -p $DEPLOY_DIR

print_info "Copying Azure Functions..."
cp -r azure_functions/* $DEPLOY_DIR/

print_info "Copying smart_data_manager_package..."
if [ ! -d "smart_data_manager_package" ]; then
    print_error "smart_data_manager_package directory not found"
    exit 1
fi
cp -r smart_data_manager_package $DEPLOY_DIR/

# Create requirements.txt
cat > $DEPLOY_DIR/requirements.txt << 'EOF'
pandas==2.2.2
SQLAlchemy==2.0.30
pyodbc>=5.1.0
azure-functions
python-dotenv==1.0.1
EOF

# Create .funcignore
cat > $DEPLOY_DIR/.funcignore << 'EOF'
.git*
.vscode
__pycache__
*.pyc
.env
local.settings.json
.venv
venv
*.md
tests/
*.log
EOF

print_success "Function package prepared"

# ============================================
# DEPLOY FUNCTION CODE
# ============================================
print_section "Deploying Function Code"

cd $DEPLOY_DIR
zip -r ../function_app.zip . -q
cd ..

print_success "Package created ($(du -h function_app.zip | cut -f1))"

print_info "Uploading to Azure (2-3 minutes)..."
az functionapp deployment source config-zip \
    --resource-group $RESOURCE_GROUP \
    --name $FUNCTION_APP_NAME \
    --src function_app.zip \
    --build-remote true \
    --timeout 900

print_success "Function code deployed"

# ============================================
# CONFIGURE STARTUP SCRIPT FOR ODBC
# ============================================
print_section "Configuring ODBC Drivers"

print_info "Setting startup command to install ODBC drivers..."
az functionapp config set \
    --resource-group $RESOURCE_GROUP \
    --name $FUNCTION_APP_NAME \
    --startup-file startup.sh \
    --output none

print_success "Startup script configured"

print_info "Restarting function app..."
az functionapp restart \
    --resource-group $RESOURCE_GROUP \
    --name $FUNCTION_APP_NAME \
    --output none

print_success "Function app restarted"

print_info "Waiting 60 seconds for startup script to complete..."
sleep 60

# ============================================
# VERIFY DEPLOYMENT
# ============================================
print_section "Verifying Deployment"

print_info "Checking Function App status..."
APP_STATE=$(az functionapp show \
    --name $FUNCTION_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query state -o tsv)
print_success "Function App state: $APP_STATE"

print_info "Listing deployed functions..."
FUNCTIONS=$(az functionapp function list \
    --name $FUNCTION_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query "[].name" -o tsv)

if [ ! -z "$FUNCTIONS" ]; then
    print_success "Functions deployed: $FUNCTIONS"
else
    print_error "No functions found - deployment may have failed"
fi

# ============================================
# COMPLETION
# ============================================
print_section "Deployment Complete!"

echo ""
echo "🎯 Your ETL is now running on Azure!"
echo ""
echo "⏰ Schedule: Runs daily at 4:00 AM UTC"
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Wait 2-3 minutes for ODBC drivers to install, then test:"
echo "   FUNCTION_KEY=\$(az functionapp function keys list \\"
echo "     --resource-group $RESOURCE_GROUP \\"
echo "     --name $FUNCTION_APP_NAME \\"
echo "     --function-name etl_function \\"
echo "     --query default -o tsv)"
echo ""
echo "   curl -X POST \"https://${FUNCTION_APP_NAME}.azurewebsites.net/api/etl_function?code=\$FUNCTION_KEY\""
echo ""
echo "2. Monitor logs:"
echo "   az webapp log tail --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP"
echo ""
echo "3. View in Azure Portal:"
echo "   https://portal.azure.com/#resource/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$FUNCTION_APP_NAME"
echo ""
echo "💡 To update code, just run this script again!"
echo ""
#!/bin/bash
set -euo pipefail

# ============================================
# CONFIG
# ============================================
RESOURCE_GROUP="rg-smart-data-manager-ready"
LOCATION="southafricanorth"

TEMPLATE_FILE="main.bicep"
DEPLOY_DIR=".azure_deploy"
ZIP_NAME="function_app.zip"

SQL_ADMIN_LOGIN="sdm-admin"

# Increase Azure CLI timeout for slow Kudu responses
export AZURE_HTTP_USER_AGENT_MODE=STRICT
export AZURE_CLI_HTTP_RETRY=5
export AZURE_BARE_HTTP_TIMEOUT=600

# ============================================
# HELPERS
# ============================================
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()    { echo -e "${GREEN}▶ $1${NC}"; }
warn()   { echo -e "${YELLOW}⚠ $1${NC}"; }
error()  { echo -e "${RED}❌ $1${NC}"; }

cleanup() {
  rm -rf "$DEPLOY_DIR" "$ZIP_NAME"
}
trap cleanup EXIT

# ============================================
# PREFLIGHT
# ============================================
log "Checking Azure CLI login"
az account show >/dev/null 2>&1 || az login

log "Checking jq"
command -v jq >/dev/null || { error "jq is required"; exit 1; }

# ============================================
# SQL PASSWORD
# ============================================
echo "🔐 Enter SQL admin password:"
read -s SQL_ADMIN_PASSWORD
echo ""
export SQL_ADMIN_PASSWORD

# ============================================
# RESOURCE GROUP
# ============================================
if ! az group exists --name "$RESOURCE_GROUP" | grep -q true; then
  log "Creating resource group"
  az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output none
else
  warn "Resource group already exists"
fi

# ============================================
# DEPLOY INFRASTRUCTURE
# ============================================
log "Deploying infrastructure (Bicep)"

DEPLOY_OUTPUT=$(az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file "$TEMPLATE_FILE" \
  --parameters \
    location="$LOCATION" \
    sqlAdminLogin="$SQL_ADMIN_LOGIN" \
    sqlAdminPassword="$SQL_ADMIN_PASSWORD" \
  --query properties.outputs \
  -o json)

FUNCTION_APP_NAME=$(echo "$DEPLOY_OUTPUT" | jq -r '.functionAppName.value')
KEY_VAULT_NAME=$(echo "$DEPLOY_OUTPUT" | jq -r '.keyVaultName.value')

if [[ -z "$FUNCTION_APP_NAME" || "$FUNCTION_APP_NAME" == "null" ]]; then
  error "Function App name not returned"
  exit 1
fi

log "Function App: $FUNCTION_APP_NAME"
log "Key Vault: $KEY_VAULT_NAME"

# ============================================
# WAIT FOR RBAC PROPAGATION
# ============================================
log "Waiting for Key Vault RBAC propagation (90s)"
sleep 90

# ============================================
# PREPARE FUNCTION PACKAGE
# ============================================
log "Preparing deployment package"

rm -rf "$DEPLOY_DIR"
mkdir "$DEPLOY_DIR"

# Copy Function App structure
cp -r ../../azure_functions/* "$DEPLOY_DIR/"

# 1. Define your Artifacts details
# It is better to set these as Environment Variables in your terminal 
# before running the script: export ARTIFACTS_PAT="your_token_here"
ORG_NAME="sinomthamzamo"
FEED_NAME="smart-data-feed"
PROJECT_NAME="smart-data-manager"
# The PAT you generated earlier
PAT="${ARTIFACTS_PAT}"
# 2. Construct the Authenticated URL
# Format: https://<ANY_USER>:<PAT>@pkgs.dev.azure.com/<ORG>/_packaging/<FEED>/pypi/simple/
FEED_URL="https://az:${PAT}@pkgs.dev.azure.com/${ORG_NAME}/${PROJECT_NAME}/_packaging/${FEED_NAME}/pypi/simple/"

log "Generating requirements.txt using private Artifacts feed..."

cat > "$DEPLOY_DIR/requirements.txt" <<EOF
--index-url $FEED_URL

azure-functions
python-dotenv==1.0.1
smart-data-manager==1.0.19
EOF

# .funcignore
cat > "$DEPLOY_DIR/.funcignore" <<EOF
.git*
.vscode
__pycache__
*.pyc
.env
tests/
*.log
smart_data_manager_package/
EOF

log "Packaging zip"
(
  cd "$DEPLOY_DIR"
  zip -r "../$ZIP_NAME" . >/dev/null
)

ZIP_SIZE=$(du -h "$ZIP_NAME" | cut -f1)
log "Zip package created ($ZIP_SIZE)"

# ============================================
# DEPLOY FUNCTION CODE
# ============================================
log "Deploying Function App code (zip deploy)"

az functionapp deployment source config-zip \
  --resource-group "$RESOURCE_GROUP" \
  --name "$FUNCTION_APP_NAME" \
  --src "$ZIP_NAME" \
  --timeout 600 \
  --output none \
  --build-remote true

log "Waiting for function startup"
sleep 30

# ============================================
# VERIFY
# ============================================
log "Verifying deployment"

APP_STATE=$(az functionapp show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$FUNCTION_APP_NAME" \
  --query state -o tsv)

log "Function App state: $APP_STATE"

log "Listing deployed functions"
FUNCTIONS=$(az functionapp function list \
  --resource-group "$RESOURCE_GROUP" \
  --name "$FUNCTION_APP_NAME" \
  --query "[].name" -o tsv || true)

if [[ -z "$FUNCTIONS" ]]; then
  warn "No functions listed yet (may still be indexing)"
else
  log "Functions:"
  echo "$FUNCTIONS"
fi

# ============================================
# DONE
# ============================================
echo ""
log "Deployment complete 🎉"
echo "Portal:"
echo "https://portal.azure.com/#resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$FUNCTION_APP_NAME"

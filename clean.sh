#!/bin/bash
# Safe cleanup script - deletes only Function App resources
# Keeps your SQL Server and Database intact

set -e

RESOURCE_GROUP="rg-smart-data-manager"

echo "🔍 Finding resources in $RESOURCE_GROUP..."

# Get all resource IDs except SQL Server and Database
RESOURCES_TO_DELETE=$(az resource list \
    --resource-group $RESOURCE_GROUP \
    --query "[?type!='Microsoft.Sql/servers' && type!='Microsoft.Sql/servers/databases'].id" \
    -o tsv)

if [ -z "$RESOURCES_TO_DELETE" ]; then
    echo "✅ No non-SQL resources to delete"
    exit 0
fi

echo ""
echo "📋 Resources to be deleted:"
az resource list \
    --resource-group $RESOURCE_GROUP \
    --query "[?type!='Microsoft.Sql/servers' && type!='Microsoft.Sql/servers/databases'].{Name:name, Type:type}" \
    -o table

echo ""
echo "⚠️  SQL Server and Database will be PRESERVED"
echo ""
read -p "Continue with deletion? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Cancelled"
    exit 1
fi

echo ""
echo "🗑️  Deleting resources (this may take 2-3 minutes)..."

# Delete each resource
for RESOURCE_ID in $RESOURCES_TO_DELETE; do
    RESOURCE_NAME=$(basename $RESOURCE_ID)
    echo "  Deleting: $RESOURCE_NAME"
    az resource delete --ids $RESOURCE_ID --verbose 2>/dev/null || echo "  ⚠️  Failed to delete $RESOURCE_NAME (may already be deleted)"
done

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Preserved resources:"
az resource list \
    --resource-group $RESOURCE_GROUP \
    --query "[].{Name:name, Type:type}" \
    -o table
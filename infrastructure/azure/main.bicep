@description('Location for all resources')
param location string = resourceGroup().location

@description('Function App name')
param functionAppName string = 'func-etl-${uniqueString(resourceGroup().id)}'

@secure()
param sqlAdminPassword string

param sqlAdminLogin string = 'sdm-admin'

@description('Existing SQL Server name (optional)')
param existingSqlServerName string = ''

@description('Existing SQL Database name (optional)')
param existingDatabaseName string = ''

// =====================
// Variables
// =====================
var storageAccountName = toLower('${uniqueString(resourceGroup().id)}funcsa')
var hostingPlanName = functionAppName
var appInsightsName = functionAppName
var keyVaultName = 'kv-etl-${take(uniqueString(resourceGroup().id), 8)}'

var sqlServerName = empty(existingSqlServerName)
  ? 'sql-etl-${uniqueString(resourceGroup().id)}'
  : existingSqlServerName

var databaseName = empty(existingDatabaseName)
  ? 'sqldb-etl'
  : existingDatabaseName

var sqlServerFqdn = '${sqlServerName}${environment().suffixes.sqlServerHostname}'

// =====================
// Storage
// =====================
resource storage 'Microsoft.Storage/storageAccounts@2022-09-01' = {
  name: storageAccountName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
}

// =====================
// App Service Plan (Linux)
// =====================
resource plan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: hostingPlanName
  location: location
  sku: {
    tier: 'Standard'
    name: 'S2'
  }
  properties: {
    reserved: true
  }
}

// =====================
// Application Insights
// =====================
resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
  }
}

// =====================
// Key Vault (RBAC)
// =====================
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enablePurgeProtection: true
    sku: {
      family: 'A'
      name: 'standard'
    }
  }
}

// =====================
// SQL Server (optional creation)
// =====================
resource sqlServer 'Microsoft.Sql/servers@2023-05-01-preview' = if (empty(existingSqlServerName)) {
  name: sqlServerName
  location: location
  properties: {
    administratorLogin: sqlAdminLogin
    administratorLoginPassword: sqlAdminPassword
    version: '12.0'
  }
}

resource sqlFirewall 'Microsoft.Sql/servers/firewallRules@2023-05-01-preview' = if (empty(existingSqlServerName)) {
  parent: sqlServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// Reference server whether created or existing
resource sqlServerRef 'Microsoft.Sql/servers@2023-05-01-preview' existing = {
  name: sqlServerName
}

// =====================
// SQL Database
// =====================
resource sqlDb 'Microsoft.Sql/servers/databases@2023-05-01-preview' = if (empty(existingDatabaseName)) {
  parent: sqlServerRef
  name: databaseName
  location: location
  sku: {
    name: 'S1'
    tier: 'Standard'
  }
  properties: {
    maxSizeBytes: 2147483648
    collation: 'SQL_Latin1_General_CP1_CI_AS'
  }
}

// =====================
// Key Vault Secrets
// =====================
resource kvDbServer 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'DB-SERVER'
  properties: {
    value: sqlServerFqdn
  }
}

resource kvDbName 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'DB-NAME'
  properties: {
    value: databaseName
  }
}

resource kvDbUser 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'DB-USERNAME'
  properties: {
    value: sqlAdminLogin
  }
}

resource kvDbPassword 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'DB-PASSWORD'
  properties: {
    value: sqlAdminPassword
  }
}

resource kvDbDriver 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'DB-DRIVER'
  properties: {
    value: 'ODBC Driver 18 for SQL Server'
  }
}

// =====================
// Function App (Linux / Python)
// =====================
resource functionApp 'Microsoft.Web/sites@2022-03-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: plan.id
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      alwaysOn: true
      appSettings: [
        { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
        { name: 'WEBSITE_RUN_FROM_PACKAGE', value: '1' }

        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccountName};AccountKey=${storage.listKeys().keys[0].value}'
        }

        { name: 'APPINSIGHTS_INSTRUMENTATIONKEY', value: insights.properties.InstrumentationKey }

        // Key Vault references
        { name: 'DB_SERVER', value: '@Microsoft.KeyVault(SecretUri=${kvDbServer.properties.secretUri})' }
        { name: 'DB_NAME', value: '@Microsoft.KeyVault(SecretUri=${kvDbName.properties.secretUri})' }
        { name: 'DB_USERNAME', value: '@Microsoft.KeyVault(SecretUri=${kvDbUser.properties.secretUri})' }
        { name: 'DB_PASSWORD', value: '@Microsoft.KeyVault(SecretUri=${kvDbPassword.properties.secretUri})' }
        { name: 'DB_DRIVER', value: '@Microsoft.KeyVault(SecretUri=${kvDbDriver.properties.secretUri})' }
      ]
    }
  }
}

// =====================
// Grant Function access to Key Vault
// =====================
resource kvRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, functionApp.id, 'kv-secrets-user')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '4633458b-17de-408a-b874-0445c86b69e6'
    )
    principalId: functionApp.identity.principalId
  }
}

// =====================
// Outputs
// =====================
output functionAppName string = functionApp.name
output sqlServerFqdn string = sqlServerFqdn
output databaseName string = databaseName
output keyVaultName string = keyVault.name

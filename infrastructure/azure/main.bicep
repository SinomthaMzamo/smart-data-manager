@description('Environment name')
@allowed([
  'dev'
  'staging'
  'prod'
])
param environment string = 'dev'

@description('Location for all resources')
param location string = resourceGroup().location

@description('SQL Server administrator login')
param sqlAdminLogin string = 'sdm-admin'

@description('SQL Server administrator password')
@secure()
param sqlAdminPassword string

@description('Existing SQL Server name (without .database.windows.net suffix)')
param existingSqlServerName string = ''

@description('Existing SQL Database name (if using existing database)')
param existingDatabaseName string = ''

// Variables
var uniqueSuffix = uniqueString(resourceGroup().id)
var functionAppName = 'func-etl-${environment}-${uniqueSuffix}'
var storageAccountName = 'stetl${environment}${take(uniqueSuffix, 8)}'
var appServicePlanName = 'asp-etl-${environment}'
var applicationInsightsName = 'appi-etl-${environment}'
var keyVaultName = 'kv-etl-${environment}-${take(uniqueSuffix, 8)}'

// Use existing or create new based on parameters
var sqlServerName = empty(existingSqlServerName) ? 'sql-etl-${environment}-${uniqueSuffix}' : existingSqlServerName
var databaseName = empty(existingDatabaseName) ? 'sqldb-etl-${environment}' : existingDatabaseName
// Use az.environment() function to get the correct SQL Server suffix for the cloud
var sqlServerFqdn = empty(existingSqlServerName) ? '${sqlServerName}${az.environment().suffixes.sqlServerHostname}' : '${existingSqlServerName}${az.environment().suffixes.sqlServerHostname}'

// Storage Account for Function App
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
  }
}

// App Service Plan (Consumption Plan for cost efficiency)
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: appServicePlanName
  location: location
  sku: {
    name: 'Y1'  // Consumption plan
    tier: 'Dynamic'
  }
  properties: {}
}

// Application Insights for monitoring
resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: applicationInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
  }
}

// Key Vault for secrets (always create new, enable purge protection)
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enabledForDeployment: false
    enabledForTemplateDeployment: true
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enablePurgeProtection: true  // Irreversible, required for security
  }
}

// SQL Server (only create if not using existing)
resource sqlServer 'Microsoft.Sql/servers@2023-05-01-preview' = if (empty(existingSqlServerName)) {
  name: sqlServerName
  location: location
  properties: {
    administratorLogin: sqlAdminLogin
    administratorLoginPassword: sqlAdminPassword
    version: '12.0'
  }
}

// Firewall rule to allow Azure services
resource sqlFirewallRule 'Microsoft.Sql/servers/firewallRules@2023-05-01-preview' = if (empty(existingSqlServerName)) {
  parent: sqlServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// SQL Database (only create if not using existing)
resource sqlDatabase 'Microsoft.Sql/servers/databases@2023-05-01-preview' = if (empty(existingDatabaseName)) {
  parent: sqlServer
  name: databaseName
  location: location
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: 2147483648  // 2GB
  }
}

// Store secrets in Key Vault
resource dbServerSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'DB-SERVER'
  properties: {
    value: sqlServerFqdn
  }
}

resource dbNameSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'DB-NAME'
  properties: {
    value: databaseName
  }
}

resource dbUsernameSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'DB-USERNAME'
  properties: {
    value: sqlAdminLogin
  }
}

resource dbPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'DB-PASSWORD'
  properties: {
    value: sqlAdminPassword
  }
}

resource dbDriverSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'DB-DRIVER'
  properties: {
    value: 'ODBC Driver 18 for SQL Server'
  }
}

// Function App
resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${az.environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${az.environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: toLower(functionAppName)
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: applicationInsights.properties.InstrumentationKey
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: applicationInsights.properties.ConnectionString
        }
        {
          name: 'DB_SERVER'
          value: '@Microsoft.KeyVault(SecretUri=${dbServerSecret.properties.secretUri})'
        }
        {
          name: 'DB_NAME'
          value: '@Microsoft.KeyVault(SecretUri=${dbNameSecret.properties.secretUri})'
        }
        {
          name: 'DB_USERNAME'
          value: '@Microsoft.KeyVault(SecretUri=${dbUsernameSecret.properties.secretUri})'
        }
        {
          name: 'DB_PASSWORD'
          value: '@Microsoft.KeyVault(SecretUri=${dbPasswordSecret.properties.secretUri})'
        }
        {
          name: 'DB_DRIVER'
          value: '@Microsoft.KeyVault(SecretUri=${dbDriverSecret.properties.secretUri})'
        }
      ]
      pythonVersion: '3.12'
    }
    httpsOnly: true
  }
}

// Grant Function App access to Key Vault using RBAC
resource keyVaultRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, functionApp.id, 'Key Vault Secrets User')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output functionAppName string = functionApp.name
output sqlServerFqdn string = sqlServerFqdn
output databaseName string = databaseName
output storageAccountName string = storageAccount.name
output applicationInsightsName string = applicationInsights.name
output keyVaultName string = keyVault.name
output functionAppPrincipalId string = functionApp.identity.principalId

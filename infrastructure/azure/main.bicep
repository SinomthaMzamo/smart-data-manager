// Azure Bicep template for ETL infrastructure
// Place this in: infrastructure/azure/main.bicep

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
param sqlAdminLogin string = 'sqladmin'

@description('SQL Server administrator password')
@secure()
param sqlAdminPassword string

@description('Existing SQL Server name (if using existing database)')
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

// Key Vault for secrets
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
        // Use the same env var names as your existing db.py
        {
          name: 'DB_SERVER'
          value: empty(existingSqlServerName) ? '${sqlServer.properties.fullyQualifiedDomainName}' : existingSqlServerName
        }
        {
          name: 'DB_NAME'
          value: databaseName
        }
        {
          name: 'DB_USERNAME'
          value: sqlAdminLogin
        }
        {
          name: 'DB_PASSWORD'
          value: sqlAdminPassword
        }
        {
          name: 'DB_DRIVER'
          value: 'ODBC Driver 18 for SQL Server'
        }
      ]
      pythonVersion: '3.12'
    }
    httpsOnly: true
  }
}

// Outputs
output functionAppName string = functionApp.name
output sqlServerFqdn string = empty(existingSqlServerName) ? sqlServer.properties.fullyQualifiedDomainName : existingSqlServerName
output databaseName string = databaseName
output storageAccountName string = storageAccount.name
output applicationInsightsName string = applicationInsights.name
output keyVaultName string = keyVault.name
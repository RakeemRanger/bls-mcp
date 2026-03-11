param location string = resourceGroup().location
param app_service_plan_name string
param func_app_name string
param func_app_msi_id string
param func_app_msi_client_id string
param environment_name string = 'dev'
param azure_search_endpoint string
param app_insights_id string
param app_insights_connection_string string
param openai_endpoint string
param model_deployment_name string

var storage_account_name = 'blsstorage${uniqueString(resourceGroup().id)}'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storage_account_name
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

resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: app_service_plan_name
  location: location
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true
  }
}

resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: func_app_name
  location: location
  kind: 'functionapp,linux'
  properties: {
    serverFarmId: appServicePlan.id
    publicNetworkAccess: 'Enabled'
    siteConfig: {
      minTlsVersion: '1.2'
      linuxFxVersion: 'Python|3.11'
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'
        }
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: toLower(func_app_name)
        }
        {
          name: 'ENVIRONMENT'
          value: environment_name
        }
        {
          name: 'AZURE_AI_INFERENCE_ENDPOINT'
          value: openai_endpoint
        }
        {
          name: 'MODEL_DEPLOYMENT_NAME'
          value: model_deployment_name
        }
        {
          name: 'AZURE_SUBSCRIPTION_ID'
          value: subscription().subscriptionId
        }
        {
          name: 'AZURE_SEARCH_ENDPOINT'
          value: azure_search_endpoint
        }
        {
          name: 'AZURE_CLIENT_ID'
          value: func_app_msi_client_id
        }
        {
          name: 'BLS_DATA_RETRIEVAL_URL'
          value: 'https://api.bls.gov/publicAPI/v2/timeseries/data/'
        }
        {
          name: 'APPLICATIONINSIGHTS_AUTHENTICATION_STRING'
          value: 'Authorization=AAD;ClientId=${func_app_msi_client_id}'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: app_insights_connection_string
        }
        {
          name: 'ApplicationInsightsAgent_EXTENSION_VERSION'
          value: '~3'
        }
        {
          name: 'InstrumentationEngine_EXTENSION_VERSION'
          value: 'disabled'
        }
      ]
      cors: {
        allowedOrigins: [
          '*'
        ]
      }
    }
  }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${func_app_msi_id}': {}
    }
  }
}

// Explicitly disable authentication for unauthenticated MCP access
resource functionAppAuthConfig 'Microsoft.Web/sites/config@2023-01-01' = {
  parent: functionApp
  name: 'authsettingsV2'
  properties: {
    globalValidation: {
      requireAuthentication: false
      unauthenticatedClientAction: 'AllowAnonymous'
    }
    httpSettings: {
      requireHttps: true
      forwardProxy: {
        convention: 'NoProxy'
      }
    }
  }
}

output func_app_endpoint string = 'https://${functionApp.properties.defaultHostName}'

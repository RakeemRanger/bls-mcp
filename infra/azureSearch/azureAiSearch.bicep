param location string = resourceGroup().location
param search_name string
param search_msi_id string
@allowed(['basic', 'standard', 'standard2', 'standard3'])
param search_sku string = 'standard'

resource azureAiSearch 'Microsoft.Search/searchServices@2025-05-01' = {
  location: location
  name: search_name
  sku: {
    name: search_sku
  }
  properties:{
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http403'
      }
    }
    publicNetworkAccess: 'Enabled'
    replicaCount: 1
    semanticSearch: 'standard'
  }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${search_msi_id}': {}
    }
  }
}

output search_resource_id string = azureAiSearch.id
output search_endpoint string = azureAiSearch.properties.endpoint

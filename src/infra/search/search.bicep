param location string = resourceGroup().location
param search_name string

resource azureAiSearch 'Microsoft.Search/searchServices@2023-11-01' = {
  name: search_name
  location: location
  sku: {
    name: 'basic'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    disableLocalAuth: false
    replicaCount: 1
    hostingMode: 'default'
    semanticSearch: 'free'
  }
}

output search_resource_id string = azureAiSearch.id
output search_principal_id string = azureAiSearch.identity.principalId

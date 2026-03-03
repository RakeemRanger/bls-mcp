param location string = resourceGroup().location
param sto_account_name string

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: sto_account_name
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    isLocalUserEnabled: false
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    defaultToOAuthAuthentication: true
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
  }
}

output sto_account_resource_id string = storageAccount.id
output sto_account_key string = storageAccount.listKeys().keys[0].value

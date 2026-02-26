param location string = resourceGroup().location
param openai_account_name string
param openai_account_msi_id string
param model_deployment_name string
param model_name string = 'gpt-4'
param model_version string = '0613'
param deployment_capacity int = 10

resource openaiAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: openai_account_name
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${openai_account_msi_id}': {}
    }
  }
  properties: {
    customSubDomainName: openai_account_name
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openaiAccount
  name: model_deployment_name
  sku: {
    name: 'Standard'
    capacity: deployment_capacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: model_name
      version: model_version
    }
  }
}

output openai_account_id string = openaiAccount.id
output openai_endpoint string = openaiAccount.properties.endpoint
output deployment_name string = modelDeployment.name

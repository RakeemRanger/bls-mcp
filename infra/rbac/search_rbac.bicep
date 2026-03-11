param func_app_msi_principal_id string
param search_resource_id string

// Search Index Data Contributor - Read/write index data
resource searchIndexDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, func_app_msi_principal_id, 'SearchIndexDataContributor', search_resource_id)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8ebe5a00-799e-43f5-93ac-243d3dce84a7')
    principalId: func_app_msi_principal_id
    principalType: 'ServicePrincipal'
  }
}

// Search Service Contributor - Manage search indexes
resource searchServiceContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, func_app_msi_principal_id, 'SearchServiceContributor', search_resource_id)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7ca78c08-252a-4471-8644-bb5ff32d4ba0')
    principalId: func_app_msi_principal_id
    principalType: 'ServicePrincipal'
  }
}

output roleAssignmentsComplete bool = true

// Role assignment for Azure AI Search
// Module scope: resourceGroup  
// Assigns role to an existing or newly created search service

@description('Principal ID (MSI) for the role assignment')
param principal_id string

@description('Search service name to assign role to')
param search_name string

@description('Display name for the role assignment')
param assignment_display_name string

@description('Azure role definition ID (full resource ID format)')
param role_definition_id string

@description('Description of the role assignment')
param role_description string

// Reference the existing search service in this resource group
resource searchService 'Microsoft.Search/searchServices@2023-11-01' existing = {
  name: search_name
}

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(principal_id, searchService.id, assignment_display_name, role_definition_id)
  scope: searchService
  properties: {
    principalId: principal_id
    principalType: 'ServicePrincipal'
    roleDefinitionId: role_definition_id
    description: role_description
  }
}

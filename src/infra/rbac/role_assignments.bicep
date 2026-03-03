// Generic role assignment module
// Assigns role at the target scope
// This module should be deployed at the same scope as the target resource

@description('Principal ID (MSI) for the role assignment')
@minLength(36)
@maxLength(36)
param principal_id string

@description('Description of the role assignment')
@minLength(1)
@maxLength(512)
param role_description string

@description('Display name for the role assignment')
@minLength(1)
@maxLength(64)
param assignment_display_name string

@description('Azure role definition ID (full resource ID format)')
param role_definition_id string

@description('Resource ID of the target resource for unique GUID generation')
param scoped_resource_id string

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(principal_id, scoped_resource_id, assignment_display_name, role_definition_id)
  properties: {
    principalId: principal_id
    principalType: 'ServicePrincipal'
    roleDefinitionId: role_definition_id
    description: role_description
  }
}

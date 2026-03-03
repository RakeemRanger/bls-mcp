// Role assignment for Azure Storage Account
// Module scope: resourceGroup
// Assigns role to an existing or newly created storage account

@description('Principal ID (MSI) for the role assignment')
param principal_id string

@description('Storage account name to assign role to')
param storage_account_name string

@description('Display name for the role assignment')
param assignment_display_name string

@description('Azure role definition ID (full resource ID format)')
param role_definition_id string

@description('Description of the role assignment')
param role_description string

// Reference the existing storage account in this resource group
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: storage_account_name
}

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(principal_id, storageAccount.id, assignment_display_name, role_definition_id)
  scope: storageAccount
  properties: {
    principalId: principal_id
    principalType: 'ServicePrincipal'
    roleDefinitionId: role_definition_id
    description: role_description
  }
}
